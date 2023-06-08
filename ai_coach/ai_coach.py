import logging

import openai
import pkg_resources
from django.conf import settings
from django.template import Context, Template
from web_fragments.fragment import Fragment
from xblock.completable import CompletableXBlockMixin
from xblock.core import XBlock
from xblock.fields import Integer, Scope, String
from xblockutils.studio_editable import StudioEditableXBlockMixin

log = logging.getLogger(__name__)


class AICoachXBlock(XBlock, StudioEditableXBlockMixin, CompletableXBlockMixin):
    """
        AI Coach xblock - Helps student to ask for improvement of their answer once
    """

    display_name = String(
            display_name='Display Name',
            help='Display name for this module',
            default="AI Coach",
            scope=Scope.settings
    )

    question = String(
            display_name='Question',
            default='',
            scope=Scope.settings,
            help='The question asked by the teacher'
    )
    student_answer = String(
            display_name='Answer',
            default='',
            scope=Scope.user_state,
            help='The answer provided by Student'
    )

    context = String(
            display_name='Context',
            default="",
            scope=Scope.settings,
            help="Write the question context here",
            multiline=True
    )

    feedback_threshold = Integer(
            default=1, scope=Scope.settings,
            help="Maximum no. of times student asks for feedback"
    )
    feedback_count = Integer(
            default=0, scope=Scope.user_state,
            help="No. of times student asks for feedback"
    )

    api_key = String(
            display_name="API Key",
            default=settings.OPENAI_SECRET_KEY,
            scope=Scope.settings,
            help="Your OpenAI API key, which can be found at <a href='https://platform.openai.com/account/api-keys' target='_blank'>https://platform.openai.com/account/api-keys</a>",
    )

    model_name = String(
            display_name="AI Model Name", values=(
                'text-davinci-003', 'text-davinci-002', 'text-curie-001', 'text-babbage-001',
                'text-ada-001'),
            default="text-davinci-003", scope=Scope.settings,
            help="Select an AI Text model."
    )

    description = String(
            default='Description here...',
            scope=Scope.settings,
            help='Any Description'
    )

    editable_fields = [
        'display_name',
        'context',
        'question',
        'model_name',
        'api_key',
        'description',
        'feedback_threshold'
    ]

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def render_template(self, template_path, context):
        """Handy helper for rendering html template."""
        template_str = self.resource_string(template_path)
        template = Template(template_str)
        context = {
            'question': self.question,
            'student_answer': self.student_answer,
            'can_request_feedback': self.feedback_count < self.feedback_threshold,
        }
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
        frag.initialize_js('AICoachXBlock')
        return frag

    def get_completion(
            self, prompt='', model='text-davinci-003', temperature=0.5, max_tokens=150, n=1
    ):
        """ Returns the improvement for student answer """

        try:
            response = openai.Completion.create(
                    prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens, n=n
            )
        except Exception as err:
            log.error(err)
            return {'error': str(err)}

        log.info(response)
        return {'response': response.choices[0].text}

    @XBlock.json_handler
    def ask_from_coach(self, data, suffix=''):

        if not data['answer']:
            return {'error': 'Answer must be required'}

        student_answer = data['answer'].strip()
        prompt = self.context.replace('{{question}}', f'"{self.question}"')
        prompt = prompt.replace('{{answer}}', f'"{student_answer}"')

        openai.api_key = self.api_key
        response = self.get_completion(prompt)

        if 'error' in response:
            return {'error': response['error']}

        coach_answer = response['response']
        self.feedback_count += 1
        return {
            'success': True,
            'coach_answer': coach_answer,
            'can_request_feedback': self.feedback_count < self.feedback_threshold
        }

    @XBlock.json_handler
    def submit_answer(self, data, suffix=''):

        if not data['answer']:
            return {'error': 'Answer must be required'}

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
