/* Javascript for AICoachXBlock. */
function AICoachXBlock(runtime, element, args) {

    let feedback_count = args.feedback_count;
    const feedback_threshold = args.feedback_threshold;

    const studentAnswer = $('#student-answer', element);
    const coachAnswerText = $('.coach-answer-text', element);
    const coachAnswerContainer = $('.coach-answer-container', element);
    const messageContainerElement = $('.message', element);
    const messageTextElement = $('.message .message__title', element);
    const tooltipElement = $('tool-tip', element);

    function showSuccessMessage() {
        messageContainerElement.addClass('bg-success');
        messageContainerElement.removeClass('message--hide');
        messageTextElement.text(gettext('Answer submitted successfully'));
    }

    function showErrorMessage(error) {
        messageContainerElement.addClass('bg-danger');
        messageContainerElement.removeClass('message--hide');
        messageTextElement.text(error);
    }

    function resetMessages() {
        messageContainerElement.removeClass('bg-danger bg-success');
        messageContainerElement.addClass('message--hide');
        messageTextElement.text('');
    }

    function updateTooltipText() {
        let tooltipText = gettext("You've exhausted all available chances to ask the coach for help")
        if (feedback_count < feedback_threshold) {
            tooltipText = edx.StringUtils.interpolate(
                gettext('You have {feedback_chances} chance{pluralize} left for requesting feedback from the coach'),
                {
                    feedback_chances: feedback_threshold - feedback_count,
                    pluralize: feedback_threshold - feedback_count > 1 ? 's' : ''
                }
            )
        }
        tooltipElement.text(tooltipText);
    }


    function showCoachAnswer(result) {
        resetMessages();
        if (result.hasOwnProperty('error')) {
            showErrorMessage(result.error);
            return;
        }

        coachAnswerText.text(result.coach_answer);
        if (result.feedback_count >= result.feedback_threshold) {
            $('.btn-ask-from-coach', element).addClass('disabled');
        }

        feedback_count = result.feedback_count;
        coachAnswerContainer.removeClass('d-none');
    }

    function submitAnswer(result) {
        resetMessages();
        if (result.hasOwnProperty('error')) {
            showErrorMessage(result.error);
            return;
        }

        showSuccessMessage();
    }

    /* ---------------------------MAKING REQUESTS TO XBLOCK BACKEND-------------------- */

    var askFromCoachUrl = runtime.handlerUrl(element, 'ask_from_coach');
    var submitAnswerUrl = runtime.handlerUrl(element, 'submit_answer');

    $('.btn-ask-from-coach', element).click(function (eventObject) {
        if (!$(this).hasClass('disabled')) {
            $.ajax({
                type: "POST",
                url: askFromCoachUrl,
                data: JSON.stringify({ 'answer': studentAnswer.val() }),
                success: showCoachAnswer
            });
        }
    });

    $('.btn-submit-answer', element).click(function (eventObject) {
        $.ajax({
            type: "POST",
            url: submitAnswerUrl,
            data: JSON.stringify({ 'answer': studentAnswer.val() }),
            success: submitAnswer
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
        /* ---------------------------UPDATE STYLES ON USER EVENTS-------------------- */
        $('.btn-ask-from-coach', element).hover(updateTooltipText);
    });
}
