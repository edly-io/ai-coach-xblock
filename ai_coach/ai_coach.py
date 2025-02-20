from xblock.utils.studio_editable import StudioEditableXBlockMixin
from xblock.fields import Float, Integer, Scope, String
from xblock.core import XBlock
from xblock.completable import CompletableXBlockMixin
from web_fragments.fragment import Fragment
from django.template import Context, Template
from django.conf import settings
import logging

from openai import OpenAI

try:
    # Older Open edX releases (Redwood and earlier) install a backported version of
    # importlib.resources: https://pypi.org/project/importlib-resources/
    import importlib_resources
except ModuleNotFoundError:
    # Starting with Sumac, Open edX drops importlib-resources in favor of the standard library:
    # https://docs.python.org/3/library/importlib.resources.html#module-importlib.resources
    from importlib import resources as importlib_resources


log = logging.getLogger(__name__)


def _(text): return text


@XBlock.wants('i18n')
class AICoachXBlock(XBlock, StudioEditableXBlockMixin, CompletableXBlockMixin):
    """
        AI Coach xblock - Helps student to ask for improvement of their answer once
    """

    display_name = String(
        display_name=_('Display Name'),
        help=_('Display name for this module'),
        default="AI Coach",
        scope=Scope.settings
    )

    question = String(
        display_name=_('Question'),
        default='',
        scope=Scope.settings,
        multiline_editor=True,
        help=_('The question asked by the teacher'),
    )
    student_answer = String(
        display_name=_('Answer'),
        default='',
        scope=Scope.user_state,
        help=_('The answer provided by Student')
    )

    context = String(
        display_name=_('Context'),
        default="",
        scope=Scope.settings,
        multiline_editor=True,
        help=_("Write the question context here"),
    )

    feedback_threshold = Integer(
        display_name=_('Feedback Threshold'),
        default=1, scope=Scope.settings,
        help=_("Maximum no. of times student asks for feedback")
    )
    feedback_count = Integer(
        default=0, scope=Scope.user_state,
        help=_("No. of times student asks for feedback")
    )

    api_key = String(
        display_name=_("API Key"),
        default=getattr(settings, 'OPENAI_SECRET_KEY', ''),
        scope=Scope.settings,
        help=_(
            "Your OpenAI API key, which can be found at \
            <a href='https://platform.openai.com/account/api-keys' target='_blank'>AI API Keys</a>"
        ),
    )

    model_name = String(
        display_name=_("AI Model Name"),
        default="gpt-3.5-turbo", scope=Scope.settings,
        help=_(
            "AI Text model to be used \
            <a href='https://platform.openai.com/docs/models/overview' target='_blank'> \
            see available models</a>"
        )
    )

    temperature = Float(
        display_name=_('Temperature'),
        default=0.5,
        values={'min': 0.1, 'max': 2, 'step': 0.1},
        scope=Scope.settings,
        help=_(
            'Higher values like 0.8 will make the output more random, \
            while lower values \n like 0.2 will make it more focused and deterministic.'
        )
    )

    description = String(
        display_name=_('Description'),
        default='Description here...',
        scope=Scope.settings,
        help=_('Any Description')
    )

    editable_fields = [
        'display_name',
        'context',
        'question',
        'model_name',
        'api_key',
        'temperature',
        'description',
        'feedback_threshold'
    ]

    def get_openai_client(self):
        """
        Initialize and return an OpenAI client using the API key stored in the XBlock settings.
        """
        api_key = self.api_key
        try:
            client = OpenAI(api_key=api_key)
            return client
        except Exception:
            # Handle the exception as appropriate for your application
            return {'error': _('Failed to initialize OpenAI client')}

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        try:
            data = importlib_resources.files(__name__).joinpath(path).read_bytes()
        except TypeError:
            data = importlib_resources.files(__package__).joinpath(path).read_bytes()
        return data.decode("utf8")

    def get_context(self):
        return {
            'title': self.display_name,
            'question': self.question,
            'student_answer': self.student_answer,
            'feedback_count': self.feedback_count,
            'feedback_threshold': self.feedback_threshold,
        }

    def render_template(self, template_path, context):
        """Handy helper for rendering html template."""
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        context = self.get_context()
        return template.render(Context(context))

    def student_view(self, context=None):
        """
        The primary view of the AITutorXBlock, shown to students
        when viewing courses.
        """

        html = self.render_template("static/html/ai_coach.html", context)
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/ai_coach.css"))
        frag.add_javascript(self.resource_string("static/js/src/ai_coach.js"))
        frag.initialize_js('AICoachXBlock', json_args=self.get_context())
        return frag

    def get_chat_completion(
            self, prompt='', model='gpt-3.5-turbo', temperature=0.5, max_tokens=150, n=1
    ):
        """ Returns the improvement for student answer using ChatGPT Model """
        client = self.get_openai_client()
        if client is None:
            return {'error': _('Unable to initialize OpenAI client. Please check configuration.')}

        messages = [{"role": "user", "content": prompt}]
        try:
            response = client.chat.completions.create(messages=messages,
                                                      model=model,
                                                      temperature=temperature,
                                                      max_tokens=max_tokens,
                                                      n=n)
        except Exception as err:
            log.error(err)
            return {'error': _('Unable to connect to AI-coach. Please contact your administrator')}

        return {'response': response.choices[0].message.content}

    @XBlock.json_handler
    def ask_from_coach(self, data, suffix=''):

        if not data['answer']:
            return {'error': _('Answer must be required')}

        if self.feedback_count >= self.feedback_threshold:
            return {'error': _("You've exhausted all available chances to ask the coach for help")}

        student_answer = data['answer'].strip()
        prompt = self.context.replace('{{question}}', f'"{self.question}"')
        prompt = prompt.replace('{{answer}}', f'"{student_answer}"')

        response = self.get_chat_completion(
            prompt, self.model_name, self.temperature
        )

        if 'error' in response:
            return {'error': response['error']}

        coach_answer = response['response']
        self.feedback_count += 1
        return {
            'success': True,
            'coach_answer': coach_answer,
            'feedback_count': self.feedback_count,
            'feedback_threshold': self.feedback_threshold
        }

    @XBlock.json_handler
    def submit_answer(self, data, suffix=''):

        if not data['answer']:
            return {'error': _('Answer must be required')}

        self.student_answer = data['answer'].strip()
        self.emit_completion(1.0)
        return {'success': True}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("AICoachXBlock",
             """<ai_coach/>
             """),
            ("Multiple AICoachXBlock",
             """<vertical_demo>
                <ai_coach/>
                <ai_coach/>
                <ai_coach/>
                </vertical_demo>
             """),
        ]
