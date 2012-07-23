from datetime import datetime
from datetime import timedelta
from django.core.cache import cache
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging
import sentry_defcon
from sentry_defcon import signals
from sentry.plugins import Plugin
from sentry.plugins import register
from sentry.filters.base import Filter
from sentry_defcon.widget import DefconWidget

logger = logging.getLogger(__name__)

COCKED_PISTOL = 1

CONDITIONS = {
    1: 'COCKED PISTOL',
    2: 'FAST PACE',
    3: 'ROUND HOUSE',
    4: 'DOUBLE TAKE',
    5: 'FADE OUT',
}

TIME_PERIODS = {
    's': 1.0,
    'm': 60.0,
    'h': 3600.0,
    'd': 86400.0,
}

class DefconConfigurationForm(forms.Form):
    condition_rate = forms.IntegerField(label=_('Condition Rate'))
    condition_rate_period = forms.ChoiceField(
        label=_('Condition Rate period'),
        choices=((p,p) for p in TIME_PERIODS.keys())
    )
    cool_down_period = forms.IntegerField(label=_('Cooldown period in seconds'))
    send_to = forms.CharField(label=_('Send to'), required=False,
        help_text=_('''
            Enter one or more emails separated by commas or lines,
            an emails will be sent when DEFCON 1 is reached
        '''),
        widget=forms.Textarea(attrs={
            'placeholder': 'you@example.com\nother@example.com'}))

class Defcon(Plugin):
    """
    An error throughput counter cache backed
    """

    title = 'Defcon'
    slug = 'sentry_defcon'
    conf_key = 'sentry_defcon'
    version = sentry_defcon.VERSION
    author = "Tommaso Barbugli"
    author_url = "https://github.com/tbarbugli/sentry_defcon"
    site_conf_form = DefconConfigurationForm

    RESOLUTION = 5
    SAMPLES = 12

    DEFAULT_RATE = 30
    DEFAULT_RATE_PERIOD = 'm'
    DEFAULT_COOL_DOWN = 600

    @property
    def condition_rate(self):
        return self.get_option('condition_rate', default=Defcon.DEFAULT_RATE)

    @property
    def condition_rate_period(self):
        return self.get_option('condition_rate_period', default=Defcon.DEFAULT_RATE_PERIOD)

    @property
    def cool_down_period(self):
        return self.get_option('cool_down', default=Defcon.DEFAULT_COOL_DOWN)

    def get_form_initial(self, project=None):
        return {
            'condition_rate': Defcon.DEFAULT_RATE,
            'condition_rate_period': Defcon.DEFAULT_RATE_PERIOD,
            'cool_down_period': Defcon.DEFAULT_COOL_DOWN,
        }

    def get_filters(self, project=None, **kwargs):
        """
        pretty ugly hack not to change base templates
        but show our fat condition status widget on 
        the project main page
        """
        DefconWidget.current_condition = self.condition()
        class F(Filter):
            widget=DefconWidget
            def get_query_set(self, queryset):
                return queryset
        F.default = self.condition()
        F.label = 'DEFCON LEVEL %.1f errors/min' % (self.get_throughput_per_second() * 60)
        return [F]

    def format_cache_key(self, dt):
        return dt.strftime("%Y-%m-%d-%H:%M:%S")

    def get_cache_keys(self, start_dt):
        keys = []
        for i in range(self.SAMPLES):
            dt = start_dt - timedelta(seconds=self.RESOLUTION * (i+1))
            keys.append(self.format_cache_key(dt))
        return keys

    def normalize_dt(self, dt):
        seconds = (dt.second/self.RESOLUTION) * self.RESOLUTION
        normalized_now = datetime(year=dt.year, month=dt.month, day=dt.day, minute=dt.minute, second=seconds)
        return normalized_now

    def get_throughput_per_second(self, dt=None):
        now = dt or datetime.now()
        keys = self.get_cache_keys(self.normalize_dt(now))
        return sum(cache.get_many(keys).values()) / float(self.SAMPLES * self.RESOLUTION)

    def update_throughput_per_second(self):
        now = datetime.now()
        normalized_now = self.normalize_dt(now)
        self.incr(normalized_now)

    def incr(self, dt):
        k = self.format_cache_key(dt)
        try:
            cache.incr(k)
        except ValueError:
            cache.set(k, 1, (self.SAMPLES * self.RESOLUTION + 1))

    def is_cocked(self):
        return bool(cache.get('SENTRY_COCKED_PISTOL_AT'))

    def set_cocked(self):
        cocked_at = cache.get('SENTRY_COCKED_PISTOL_AT')
        cache.set('SENTRY_COCKED_PISTOL_AT', cocked_at or datetime.now(),
                  self.cool_down_period)
        signals.defcon_one_reached.send(sender=self)

    def condition(self):
        """
        returns the defcon condition 1 ... 5
        1 is the most severe, 5 the most relaxed
        calcaluation is based on how many times the throughput is compared
        to self.condition_rate
        if condition goes to COCKED PISTOL it will stay there for
        at least self.condition_rate_period seconds

        """
        if self.is_cocked():
            return COCKED_PISTOL
        return self.calculate_condition()

    def calculate_condition(self):
        throughput = self.get_throughput_per_second()
        threshold = self.condition_rate / TIME_PERIODS[self.condition_rate_period]
        logger.debug("current throughput is %f/s" % throughput)
        try:
            condition = 5 - min(int(throughput / threshold), 4)
        except ZeroDivisionError:
            condition = 5
        if condition == COCKED_PISTOL:
            self.set_cocked()
        logger.debug("current condition is %r" % condition)
        return condition

    def post_process(self, group, event, is_new, is_sample, **kwargs):
        self.update_throughput_per_second()
        self.condition()

register(Defcon)

def notify_defcon_one(sender, **kwargs):
    emails = sender.get_option('send_to') or []
    if isinstance(emails, basestring):
        emails = [s.strip() for s in emails.split(',')]
    msg = EmailMultiAlternatives(
        'Defcon 1 reached!',
        'We reached DEFCON 1, error rate reached errors per seconds!',
        settings.SENTRY_SERVER_EMAIL,
        emails
    )
    msg.send(fail_silently=True)

signals.defcon_one_reached.connect(notify_defcon_one)
