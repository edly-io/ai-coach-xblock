"""TO-DO: Write a description of what this XBlock is."""

import logging
import pkg_resources
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Scope, String
from xblockutils.studio_editable import StudioEditableXBlockMixin
import openai
from django.template import Context, Template
from django.conf import settings


log = logging.getLogger(__name__)


class AITutorXBlock(XBlock, StudioEditableXBlockMixin):
    """
        AI tutor xblock - Helps student to ask for improvement of their answer once
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
        default="",
        scope=Scope.settings,
        help="Write the question context here",
        multiline=True
    )

    is_allowed_for_coach_help = Boolean(default=True, scope=Scope.user_state,
                                        help="If true, then student can "
                                        "ask from coach.")

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
        'description'
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
            'is_allowed_for_coach_help': self.is_allowed_for_coach_help,
        }
        return template.render(Context(context))

    def student_view(self, context=None):
        """
        The primary view of the AITutorXBlock, shown to students
        when viewing courses.
        """

        html = self.render_template("static/html/ai_tutor.html", context)
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/ai_tutor.css"))
        frag.add_javascript(self.resource_string("static/js/src/ai_tutor.js"))
        frag.initialize_js('AITutorXBlock')
        return frag

    def get_completion(self, prompt='', model='text-davinci-003', temperature=0.5, max_tokens=150, n=1):
        """
            Returns the improvement for student answer
        """
        try:
            response = openai.Completion.create(
                prompt=prompt, model=model, temperature=temperature, max_tokens=max_tokens, n=n)
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
        prompt = self.context.replace(
            '{{question}}', f'"{self.question}"')
        prompt = prompt.replace('{{answer}}', f'"{student_answer}"')

        openai.api_key = self.api_key
        response = self.get_completion(prompt)

        if 'error' in response:
            return {'error': response['error']}

        coach_answer = response['response']
        self.is_allowed_for_coach_help = False
        return {'question': self.question, 'student_answer': student_answer, 'coach_answer': coach_answer, 'is_allowed_for_coach_help': self.is_allowed_for_coach_help}

    @XBlock.json_handler
    def submit_answer(self, data, suffix=''):

        if not data['answer']:
            return {'error': 'Answer must be required'}

        self.student_answer = data['answer'].strip()
        return {'question': self.question, 'student_answer': self.student_answer}

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("AITutorXBlock",
             """<ai_tutor/>
             """),
            ("Multiple AITutorXBlock",
             """<vertical_demo>
                <ai_tutor/>
                <ai_tutor/>
                <ai_tutor/>
                </vertical_demo>
             """),
        ]
