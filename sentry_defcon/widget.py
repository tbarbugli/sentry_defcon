from sentry.filters.widgets import Widget
from django.utils.safestring import mark_safe

class DefconWidget(Widget):
    current_condition = None
    def render(self, value, placeholder='', **kwargs):
        from sentry_defcon.models import CONDITIONS
        level_list = [
            '<ul class="nav nav-tabs nav-stacked filter-list" rel="defcon">'
        ]
        level = '<li><a href="#">%s</a></li>'
        active_level = '<li class="active"><a href="#">%s</a></li>'
        for condition in CONDITIONS.keys():
            tmpl = level
            if condition == DefconWidget.current_condition:
                tmpl = active_level
            level_list.append(tmpl % CONDITIONS[condition])
        level_list.append('</ul>')
        return mark_safe(''.join(level_list))
