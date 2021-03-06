from datetime import datetime, date, timedelta
import hashlib
import itertools
import re
import uuid

from geopy.geocoders import Nominatim

from constance import config

import django.utils
import django.utils.text
from django.conf import settings
from django.db import models
from django.urls import reverse

from simple_history.models import HistoricalRecords

from django_countries.fields import CountryField

import tagulous.models

from .validator import pdf, online_document
from .jacs import JACS_3_0_PRINCIPAL_SUBJECT_CODES
from .utils import ChoicesEnum

INVOICE_HASH = hashlib.md5()

MAX_CHAR_LENGTH = 120
MAX_URL_LENGTH = 360
MAX_INVOICE_REFERENCE_LENGTH = 14  # e.g. SSIF-xxxx-xxxx
MAX_PHONE_LENGTH = 14
MAX_DIGITS = 10

GENDERS = (
    ('M', 'Male'),
    ('F', 'Female'),
    ('O', 'Other'),
    ('R', 'Rather not say'),
)

CAREER_STAGES = (
    ('1', 'Phase 1 - Junior (e.g. PhD candidate, Junior Research Software Engineer)'),
    ('2', 'Early (e.g Research Assistant/Associate, first grant holder, Lecturer, Research Software Engineer)'),
    ('3', 'Mid / Recognised (e.g. Senior Lecturer, Reader, Senior Researcher, Senior Research Software Engineer, Research Software Group Leader)'),
    ('4', 'Established / Experienced / Senior  (e.g. Professor, Director of Research Computing, Distinguished Engineer, Chief Data Scientist)'),
)

FUND_CATEGORY = (
    ('A', 'Attending'),
    ('H', 'Organising'),
)

FUND_FOCUS = (
    ('D', 'Domain specific'),
    ('C', 'Cross cutting'),
)

class FundActivity(tagulous.models.TagTreeModel):  # pylint: disable=model-no-explicit-unicode
    class Meta:
        verbose_name = 'Fund Activity Tag'
        verbose_name_plural = 'Fund Activity Tags'
        ordering = [
            "name",
        ]

    class TagMeta:
        initial = "attending as ssi, conference, field trip, focus group, hack, knowledge exchange, local, meeting, new paradigm, new resource, organising submeeting, panel, paying for others, policy, poster presentation, prize, roundtable, roundtable/lead, software Special Interest Group, ssi organised, supported collaborator, survey, talk at, talk at/invited, teaching at, teaching as helper, training/attending, training/organiser, unconference, working group, workshop"
        force_lowercase = True
        autocomplete_view = None
        protected = True
        space_delimiter = False

AD_STATUS = (
    ('U', 'Unprocessed'),  # Initial status
    ('V', 'Visible'),  # Fund is visible on map
    ('H', 'Hide'),  # Fund is invisible on map
)

FUND_STATUS = (
    ('U', 'Unprocessed'),  # Initial status
    ('P', 'Processing'),  # When someone was assigned to review the request
    ('A', 'Approved'),  # Fund was approved. Funds are reserved.
    ('M', 'Approved'),  # Fund was approved by machine. Funds are reserved.
    ('R', 'Rejected'),  # Fund was rejected.
    ('F', 'Archived'),  # Approved funds with all claims and blog posts were processed. No funds are reserved.
    ('C', 'Cancelled'),  # When the fellow decided to cancel their request.
    ('X', 'Remove'),  # When the fellow decided to remove their request.
)

#: Set of statuses which constitute an approved fund
FUND_STATUS_APPROVED_SET = {
    'A',
    'M',
}

FUND_STATUS_LONG_DESCRIPTION = {
    'U': "We didn't start to process your request yet.",
    'P': "One of your staffs is reviewing your request. You should have our reply soon.",
    'A': "Your fund request was approved.",
    'M': "Your fund request was pre-approved.",
    'R': "Your fund request was declided.",
    'F': "We archived your fund request since all the expense claims were processed.",
    'C': "You decided to cancel this request for any reason.",
}

EXPENSE_STATUS = (
    ('S', 'Submitted'),
    ('C', 'Processing'),
    ('A', 'Approved'),
    ('R', 'Rejected'),  # When expense was rejected.
    ('X', 'Remove'),  # When the fellow decided to remove their request.
)

GRANT_HEADING = (
    ('C', 'Continuing (claimantship)'),
    ('I', 'Core (Software Sustainability Institute)'),
    ('F', 'Grant (inauguration claimantship)'),
)

GRANTS = (
    ('SSI1', 'Software Sustainability Institute - Phase 1'),
    ('SSI2', 'Software Sustainability Institute - Phase 2'),
    ('SSI3', 'Software Sustainability Institute - Phase 3'),
    ('SSI4', 'Software Sustainability Institute - Phase 4'),
)

BLOG_POST_STATUS = (
    ('U', 'Waiting for triage'),  # This is the status after we receive the blog post draft.
    ('R', 'Waiting to be reviewed'),  # Blog post is assigned to one staff to be reviewed.
    ('C', 'Reviewing loop'),  # Blog post is waiting for another reviewing interaction.
    ('G', 'Waiting to be proofread'),  # Blog post is assigned to be proofread by the community officer.
    ('L', 'Waiting to be published'),  # Blog post will be publish by the community officer.
    ('P', 'Published'),  # Blog post is published and have a URL at the website.
    ('M', 'Mistaked'),  # Blog post submitted by mistake.
    ('D', 'Rejected'),  # Blog post is rejected for any reason.
    ('O', 'Out of date'),  # Blog post that wait too long to be publish for any reason.
    ('X', 'Remove'),  # When the fellow decided to remove their request.
)


class ApprovalChain(ChoicesEnum):
    """
    Which approval chain is required to authorise this request?
    """
    FELLOWS = "fellows"
    ONE_TIME = "onetime"

    @classmethod
    def email_address(cls, chain):
        if chain == cls.FELLOWS:
            return config.FELLOWS_MANAGEMENT_EMAIL

        if chain == cls.ONE_TIME:
            return config.ONETIME_APPROVAL_EMAIL

        raise ValueError("Approval chain has not been fully defined")


def fix_url(url):
    """Prepend 'http://' to URL."""
    if url is not None and url:
        url = url.split()[0]  # If the URL uses white space it should be encoded as %20%
        url = url.split(",")[0]  # If the URL uses comma it should be encoded as %2C.
        if not re.match("https?://", url):
            url = "http://{}".format(url)

    return url

def pair_fund_with_blog(funds, status=None):
    """Create list of tuples where first element is fund and second is list of blog related with it."""
    args = {}
    if status:
        args["status"] = status

    return [(fund, Blog.objects.filter(
        fund=fund,
        **args
    )) for fund in funds]


class TermsAndConditions(models.Model):
    """Terms and Conditions information."""
    class Meta:
        ordering = [
            "-year",
        ]
        verbose_name_plural = "terms and conditions"

    #: Programme year for which this terms and conditions page is valid
    year = models.CharField(  # Year as string so it can be used for special cases.
        max_length=4,  # YYYY
        primary_key=True
    )

    #: URL of terms and conditions page
    url = models.CharField(  # External web page.
        max_length=MAX_CHAR_LENGTH
    )

    def __str__(self):
        return "{} Terms & Conditions".format(
            self.year
        )


class Claimant(models.Model):
    """Describe a claimant."""

    class Meta:
        app_label = 'lowfat'
        ordering = [
            "-fellow",
            "-application_year",
            "forenames",
            "surname",
        ]

    # Authentication
    #
    # We use this to only allow claimant to access their own data.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True
    )

    # Personal info (application details)
    forenames = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=False
    )
    surname = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=False
    )
    email = models.EmailField(
        blank=False
    )
    phone = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=False,
        help_text="The number that we can contact you."
    )
    gender = models.CharField(
        choices=GENDERS,
        max_length=1,
        default="R"
    )
    home_country = CountryField(
        blank=False,
        default='GB'  # Default for United Kingdom
    )
    home_city = models.CharField(
        blank=False,
        max_length=MAX_CHAR_LENGTH
    )
    home_lon = models.FloatField(
        null=True,
        blank=True
    )
    home_lat = models.FloatField(
        null=True,
        blank=True
    )
    photo = models.FileField(
        upload_to='photos/',  # File will be uploaded to MEDIA_ROOT/photos
        null=True,
        blank=True,  # This need to be a JPG.
        help_text="A professionally oriented (i.e. work related) thumbnail picture of yourself that you are happy to be published on the web - this should be 150px wide and 150px high (exact please)."
    )

    # Professional info
    career_stage_when_apply = models.CharField(
        choices=CAREER_STAGES,
        max_length=1,
        default="M"
    )
    job_title_when_apply = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    research_area = models.TextField(
        blank=True,
        help_text="Please describe your research"
    )
    # JACS code for research_area.
    # https://www.hesa.ac.uk/jacs/
    research_area_code = models.CharField(
        choices=JACS_3_0_PRINCIPAL_SUBJECT_CODES,
        max_length=2,
        default="Y0"
    )
    affiliation = models.CharField(  # Home institution
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    department = models.CharField(  # Department within home institution
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    group = models.CharField(  # Group within department
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    funding = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    funding_notes = models.TextField(
        null=True,
        blank=True
    )

    # Website
    #
    # See https://www.software.ac.uk/fellows/
    interests = models.TextField(
        blank=True,
        help_text="25-50 word summary of your professional interests."
    )
    work_description = models.TextField(
        blank=True,
        help_text="200-300 words describing the work you do, this can include your plans for Fellowship."
    )
    photo_work_description = models.FileField(
        upload_to='photos/',  # File will be uploaded to MEDIA_ROOT/photos
        null=True,
        blank=True,  # This need to be a JPG.
        help_text="A professionally oriented (i.e. work related) main picture of yourself that you are happy to be published on the web - this should be 300px wide and 400px high (exact please)."
    )

    # Social media
    institutional_website = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True
    )
    website = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True
    )
    website_feed = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True
    )
    orcid = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    google_scholar = models.CharField(  # For example, https://scholar.google.co.uk/citations?user=XXXXXXXXXXXX
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    github = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    gitlab = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    bitbucket = models.CharField(  # https://bitbucket.org/
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    twitter = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    linkedin = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    facebook = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )

    # Admin fields
    slug = models.CharField(max_length=MAX_CHAR_LENGTH)
    terms_and_conditions = models.ForeignKey(
        'TermsAndConditions',
        null=True,
    )
    application_year = models.IntegerField(
        null=False,
        blank=False,
        default=date.today().year
    )
    inauguration_grant_expiration = models.DateField(
        null=False,
        blank=False,
        default=date(  # This will be overwrite by save().
            date.today().year + 2,
            3,
            31
        )
    )
    shortlisted = models.BooleanField(default=False)
    received_offer = models.BooleanField(default=False)
    fellow = models.BooleanField(default=False)
    collaborator = models.BooleanField(default=False)
    is_into_training = models.BooleanField(default=False)
    carpentries_instructor = models.BooleanField(default=False)
    research_software_engineer = models.BooleanField(default=False)
    claimantship_grant = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        null=False,
        blank=False,
        default=0.00
    )
    attended_inaugural_meeting = models.BooleanField(default=False)
    attended_collaborations_workshop = models.BooleanField(default=False)  # pylint: disable=invalid-name
    notes_from_admin = models.TextField(
        null=True,
        blank=True
    )

    # Application
    screencast_url = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True,  # See https://github.com/softwaresaved/lowfat/issues/192
    )
    example_of_writing_url = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True,  # See https://github.com/softwaresaved/lowfat/issues/192
    )

    # Mentors need to be another claimant
    mentor = models.ForeignKey(
        'self',
        blank=True,
        null=True
    )

    # Control
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def get_absolute_url(self):
        return reverse('claimant-slug-resolution', kwargs={'claimant_slug': self.slug})

    def slug_generator(self):
        """
        Generate slug for Claimant - checking that it doesn't conflict with an existing Claimant.
        """
        base_slug = django.utils.text.slugify("{0}-{1}".format(self.forenames, self.surname))
        slug = base_slug

        for i in itertools.count():
            try:
                # Has this slug already been used?
                existing = Claimant.objects.get(slug=slug)
                if existing.pk == self.pk:
                    break

            except Claimant.DoesNotExist:
                # No - use this slug
                break

            except Claimant.MultipleObjectsReturned:
                # Yes - multiple times - try the next one
                pass

            # Yes - try the next one
            slug = '{0}-{1}'.format(base_slug, i)

        return slug

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if not self.id:
            self.inauguration_grant_expiration = date(
                date.today().year + 2,
                config.FELLOWSHIP_EXPENSES_END_MONTH,
                config.FELLOWSHIP_EXPENSES_END_DAY
            )

        if not self.slug:
            self.slug = self.slug_generator()

        self.website = fix_url(self.website)
        self.website_feed = fix_url(self.website_feed)

        super(Claimant, self).save(*args, **kwargs)

    def update_latlon(self):
        geolocator = Nominatim(
            country_bias=self.home_country,
            user_agent="lowfat/dev"
        )
        try:
            location = geolocator.geocode(
                self.home_city
            )
            if location is not None:
                self.home_lon = location.longitude
                self.home_lat = location.latitude

                self.save()
        except Exception as exception:  # pylint: disable=broad-except
            print(exception)

    def __str__(self):
        return "{} ({}{})".format(
            self.fullname(),
            self.application_year + 1,
            " ✓" if self.fellow else ""
        )

    def fullname(self):
        return "{} {}".format(self.forenames, self.surname)

    def link(self):
        if self.fellow:
            function_name = "fellow_slug"
        else:
            function_name = "claimant_slug"
        return reverse(function_name, args=[self.slug])

    def fullname_link(self):
        return """<a href="{}">{} {}</a>""".format(
            self.link(),
            self.forenames,
            self.surname
        )

    def claimantship_available(self):
        """Return the remaining claimantship grant."""
        money_available = 0
        if self.inauguration_grant_expiration > date.today():
            money_available = self.claimantship_grant - self.claimantship_committed() - self.claimantship_spent()

        return money_available

    def claimantship_passed(self):
        """Return the amount already spent from the claimantship grant."""
        money_passed = 0
        if self.inauguration_grant_expiration < date.today():
            money_passed = self.claimantship_grant - self.claimantship_committed() - self.claimantship_spent()

        return money_passed

    def claimantship_committed(self):
        """Return the amount committed from the claimantship grant."""
        this_claimant_funds = Fund.objects.filter(
            claimant=self,
            status__in=FUND_STATUS_APPROVED_SET,
            grant_heading="F"
        )

        spent_from_committed = 0
        for fund in this_claimant_funds:
            spent_from_committed += sum([expense.amount_claimed for expense in Expense.objects.filter(
                fund=fund,
                status__in=['A', 'M', 'F']
            )])

        return sum([fund.budget_approved for fund in this_claimant_funds]) - spent_from_committed

    def claimantship_spent(self):
        """Return the amount already spent from the claimantship grant."""
        this_claimant_expenses = Expense.objects.filter(
            fund__claimant=self,
            status__in=['A', 'M', 'F'],
            grant_heading="F"
        )

        return sum([expense.amount_claimed for expense in this_claimant_expenses])


class ModelWithToken(models.Model):
    class Meta:
        abstract = True

    # Access token
    access_token = models.CharField(
        max_length=32,
        null=True,
        blank=True
    )
    access_token_expire_date = models.DateField(
        null=True,
        blank=True
    )

    def new_access_token(self):
        self.access_token = uuid.uuid4().hex
        self.access_token_expire_date = date.today() + timedelta(days=30)
        self.save()

    def access_token_is_valid(self):
        if self.access_token_expire_date is not None:
            return date.today() < self.access_token_expire_date

        return False


class Fund(ModelWithToken):
    """Describe a fund from one claimant."""
    class Meta:
        app_label = 'lowfat'
        ordering = [
            "-start_date",
            "-end_date",
            "title",
        ]

    # TODO Make claimant more generic to include staffs.
    claimant = models.ForeignKey('Claimant')
    category = models.CharField(
        choices=FUND_CATEGORY,
        max_length=1,
        default="A"
    )
    focus = models.CharField(
        choices=FUND_FOCUS,
        max_length=1,
        default="C"
    )
    activity = tagulous.models.TagField(
        to=FundActivity,
        blank=True
    )
    mandatory = models.BooleanField(default=False)
    title = models.CharField(max_length=MAX_CHAR_LENGTH)
    url = models.CharField(
        max_length=MAX_URL_LENGTH,
        blank=True,  # See https://github.com/softwaresaved/lowfat/issues/192
    )
    country = CountryField(default='GB')  # Default for United Kingdom
    city = models.CharField(max_length=MAX_CHAR_LENGTH)
    lon = models.FloatField(
        null=True,
        blank=True
    )
    lat = models.FloatField(
        null=True,
        blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    budget_request_travel = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_request_attendance_fees = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_request_subsistence_cost = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_request_venue_hire = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_request_catering = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_request_others = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    budget_approved = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        default=0.00
    )
    justification = models.TextField()
    success_targeted = models.TextField(
        help_text="Please specify what outputs (what maybe be produced) and outcomes (what change it could lead to) are likely to be produced from your participation in this event. These can include learning goals being met, collaborations, reports etc."
    )
    success_reported = models.TextField(blank=True)  # Only provide later
    additional_info = models.TextField(blank=True)
    extra_sponsored = models.TextField(blank=True)

    # Publicity
    can_be_included_in_calendar = models.BooleanField(default=False)  # For privacy.
    can_be_advertise_before = models.BooleanField(default=False)  # For privacy.
    can_be_advertise_after = models.BooleanField(default=True)  # For fulfilment of contract.

    # Admin fields
    ad_status = models.CharField(
        choices=AD_STATUS,
        max_length=1,
        default="U"
    )
    status = models.CharField(
        choices=FUND_STATUS,
        max_length=1,
        default="U"
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True
    )
    required_blog_posts = models.IntegerField(
        null=False,
        blank=True
    )
    grant_heading = models.CharField(
        choices=GRANT_HEADING,
        max_length=1,
        default="F"
    )
    grant = models.CharField(
        choices=GRANTS,
        max_length=4,
        default="SSI3"
    )
    notes_from_admin = models.TextField(
        null=True,
        blank=True
    )

    # Control
    added = models.DateTimeField(auto_now_add=True)
    approved = models.DateTimeField(
        null=True,
        blank=True
    )
    updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    #: Who is required to approve this request?
    approval_chain = models.CharField(
        choices=ApprovalChain.choices(),
        max_length=8,
        default=ApprovalChain.FELLOWS
    )

    def remove(self):
        self.status = "X"
        self.save()

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if not self.pk:
            self.grant = config.GRANTS_DEFAULT
            if date.today() < self.claimant.inauguration_grant_expiration:
                self.grant_heading = "F"
            else:
                self.grant_heading = "C"

        if self.status in FUND_STATUS_APPROVED_SET:
            self.approved = datetime.now()

        if self.required_blog_posts is None:
            # Blog posts are not required if an event is mandatory - e.g. collaborations workshop
            self.required_blog_posts = 0 if self.mandatory else 1

        self.url = fix_url(self.url)

        super(Fund, self).save(*args, **kwargs)

    def update_latlon(self):
        geolocator = Nominatim(
            country_bias=self.country,
            user_agent="lowfat/dev"
        )
        try:
            location = geolocator.geocode(
                self.city
            )
            if location is not None:
                self.lon = location.longitude
                self.lat = location.latitude

                self.save()
        except Exception as exception:  # pylint: disable=broad-except
            print(exception)

    def __str__(self):
        return "{} ({})".format(self.title, self.id)

    def status_help(self):
        """Provide long description for the status."""

        # XXX Propably there is a better way to do this.
        return FUND_STATUS_LONG_DESCRIPTION[self.status]

    def budget_total(self):
        """Return the sum of all `budget_request`s."""
        return sum(
            [
                self.budget_request_travel,
                self.budget_request_attendance_fees,
                self.budget_request_subsistence_cost,
                self.budget_request_venue_hire,
                self.budget_request_catering,
                self.budget_request_others,
            ]
        )

    def expenses_claimed(self):
        """Return the total amount of expenses claimant."""
        this_fund_expenses = Expense.objects.filter(
            fund=self,
            status__in=["S", "C", "A", "M"]
        )
        return sum([expense.amount_claimed for expense in this_fund_expenses])

    def expenses_claimed_left(self):
        """Return the total amount left to claimant."""
        return self.budget_total() - self.expenses_claimed()

    def expenses_authorized_for_payment(self):
        """Return the total amount of expenses authorized_for_payment."""
        this_fund_expenses = Expense.objects.filter(
            fund=self,
            status__in=FUND_STATUS_APPROVED_SET
        )
        return sum([expense.amount_authorized_for_payment for expense in this_fund_expenses])

    def total_of_blog_posts(self):
        """Return number of blog posts."""
        return Blog.objects.filter(fund=self).count()

    def link(self):
        if self.access_token:
            link = reverse("fund_detail_public", args=[self.access_token])
        else:
            link = reverse("fund_detail", args=[self.id])
        return link

    def title_link(self):
        return """<a href="{}">{}</a>""".format(
            self.link(),
            self.title
        )

    def link_review(self):
        return reverse("fund_review", args=[self.id])

    def pre_approve(self):
        approved = False

        if self.mandatory and self.budget_total() < config.PRE_APPROVED_FUNDING_REQUEST_BUDGET:
            self.status = 'M'
            self.save()
            approved = True

        return approved

    def new_access_token(self):
        self.access_token = uuid.uuid4().hex
        today = date.today()
        if today < self.end_date:
            self.access_token_expire_date = self.end_date + timedelta(days=30)
        else:
            self.access_token_expire_date = today + timedelta(days=30)
        self.save()


class Expense(ModelWithToken):
    """This describe one expense for one fund."""
    class Meta:
        app_label = 'lowfat'
        ordering = [
            "-added",
            "relative_number",
        ]

    # Internal
    relative_number = models.IntegerField(
        null=False,
        blank=False
    )
    invoice_reference = models.CharField(
        max_length=MAX_INVOICE_REFERENCE_LENGTH,
        null=True,
        blank=True
    )

    # Form
    fund = models.ForeignKey('Fund')
    claim = models.FileField(
        upload_to='expenses/',  # File will be uploaded to MEDIA_ROOT/expenses
        validators=[pdf]
    )
    amount_claimed = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        blank=False,
        default=0.00
    )
    justification_for_extra = models.TextField(
        blank=True
    )
    invoice = models.BooleanField(
        default=False
    )
    final = models.BooleanField(
        default=False
    )
    advance_booking = models.BooleanField(
        default=False
    )
    # Recipient
    recipient_fullname = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    recipient_email = models.EmailField(
        blank=True
    )
    recipient_affiliation = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    recipient_group = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True
    )
    recipient_connection = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        blank=True,
        help_text="You need to provide a reason for submit the recipient claim. An common reasons is \"because the recipient was of of the speakers on that workshop.\""
    )

    # Admin fields
    status = models.CharField(
        choices=EXPENSE_STATUS,
        max_length=1,
        default="S"
    )
    asked_for_authorization_date = models.DateField(
        blank=True,
        null=True
    )
    send_to_finance_date = models.DateField(
        blank=True,
        null=True
    )
    amount_authorized_for_payment = models.DecimalField(
        max_digits=MAX_DIGITS,
        decimal_places=2,
        blank=False,
        default=0.00
    )
    grant_heading = models.CharField(
        choices=GRANT_HEADING,
        max_length=1,
        default="F"
    )
    grant = models.CharField(
        choices=GRANTS,
        max_length=4,
        default="SSI3"
    )
    notes_from_admin = models.TextField(
        null=True,
        blank=True
    )

    # Control
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return "Expense {} - {}".format(
            self.id,
            self.claim.name
        )

    def remove(self):
        self.status = "X"
        self.save()

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        if self.pk is None:
            previous_expenses = Expense.objects.filter(fund=self.fund).order_by("-pk")
            if previous_expenses:
                self.relative_number = previous_expenses[0].relative_number + 1
            else:
                self.relative_number = 1

            if self.fund.mandatory:  # pylint: disable=no-member
                self.grant_heading = 'I'  # Use of Core fund
            else:
                self.grant_heading = self.fund.grant_heading  # pylint: disable=no-member
            self.grant = self.fund.grant  # pylint: disable=no-member

            if self.invoice:
                INVOICE_HASH.update(bytes("{} - {} #{}".format(
                    self.fund.claimant.fullname,  # pylint: disable=no-member
                    self.fund.title,
                    self.relative_number
                ), 'utf-8'))
                self.invoice_reference = "SSIF-{}-{}".format(
                    INVOICE_HASH.hexdigest()[0:5],
                    INVOICE_HASH.hexdigest()[5:9]
                )

        super(Expense, self).save(*args, **kwargs)

    def link(self):
        if self.access_token:
            link = reverse("expense_detail_public", args=[self.access_token])

        else:
            link = reverse("expense_detail_relative", args=[self.fund.id, self.relative_number])

        return link

    def link_review(self):
        return reverse("expense_review_relative", args=[self.fund.id, self.relative_number])

    def link_claim(self):
        return reverse("expense_claim_relative", args=[self.fund.id, self.relative_number])

    def claim_clean_name(self):
        return "{}".format(
            self.claim.name.replace("/", "-")
        )


class Blog(ModelWithToken):
    """Provide the link to the blog post about the fund."""
    class Meta:
        app_label = 'lowfat'
        ordering = [
            "-added",
        ]

    # Form
    fund = models.ForeignKey(
        'Fund',
        null=True,
        blank=True
    )
    author = models.ForeignKey(
        'Claimant',
        null=True,
        blank=True
    )
    coauthor = models.ManyToManyField(
        'Claimant',
        blank=True,
        related_name="author"
    )
    draft_url = models.CharField(
        max_length=MAX_URL_LENGTH,
        validators=[online_document]
    )
    final = models.BooleanField(
        default=False
    )
    notes_from_author = models.TextField(
        null=True,
        blank=True
    )

    # Admin fields
    status = models.CharField(
        choices=BLOG_POST_STATUS,
        max_length=1,
        default="U"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True
    )
    notes_from_admin = models.TextField(
        null=True,
        blank=True
    )
    title = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        null=True,
        blank=True
    )
    published_url = models.CharField(
        max_length=MAX_URL_LENGTH,
        null=True,
        blank=True
    )
    tweet_url = models.CharField(
        max_length=MAX_URL_LENGTH,
        null=True,
        blank=True
    )

    # Control
    added = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def remove(self):
        self.status = "X"
        self.save()

    def save(self, *args, **kwargs):  # pylint: disable=arguments-differ
        self.draft_url = fix_url(self.draft_url)
        self.published_url = fix_url(self.published_url)
        self.tweet_url = fix_url(self.tweet_url)

        if self.published_url:
            self.status = 'P'
        super(Blog, self).save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.draft_url)

    def link(self):
        if self.access_token:
            link = reverse("blog_detail_public", args=[self.access_token])
        else:
            link = reverse("blog_detail", args=[self.id])
        return link

    def link_review(self):
        return reverse("blog_review", args=[self.id])

class GeneralSentMail(models.Model):
    """Emails sent with custom text."""
    class Meta:
        app_label = 'lowfat'
        ordering = [
            "date",
        ]

    justification = models.TextField()

    # Internal
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,  # For confirmation email
    )
    receiver = models.ForeignKey('Claimant')
    date = models.DateField(default=django.utils.timezone.now)
    history = HistoricalRecords()


class FundSentMail(GeneralSentMail):
    fund = models.ForeignKey('Fund')


class ExpenseSentMail(GeneralSentMail):
    expense = models.ForeignKey('Expense')


class BlogSentMail(GeneralSentMail):
    blog = models.ForeignKey('Blog')
