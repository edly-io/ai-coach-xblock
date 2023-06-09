/* Javascript for AICoachXBlock. */
function AICoachXBlock(runtime, element) {

    const studentAnswer = $('#student-answer', element);
    const coachAnswer = $('.coach-answer p', element);
    const messageElement = $('.messages', element);

    function showCoachAnswer(result) {
        removeClassesFromMsgElement();

        if (result.hasOwnProperty('error')) {
            messageElement.addClass('error');
            messageElement.text(result.error);
            return;
        }

        messageElement.text('');
        coachAnswer.text(result.coach_answer);

        $('.ask-from-coach', element).hide();
        $('.coach-answer ', element).show();
    }

    function submitAnswer(result) {
        removeClassesFromMsgElement();

        if (result.hasOwnProperty('error')) {
            messageElement.addClass('error');
            messageElement.text(result.error);
            return;
        }

        messageElement.text('Answer submitted successfully');
        messageElement.addClass('success');
    }

    function removeClassesFromMsgElement() {
        messageElement.removeClass('error');
        messageElement.removeClass('success');
    }

    var askFromCoachUrl = runtime.handlerUrl(element, 'ask_from_coach');
    var submitAnswerUrl = runtime.handlerUrl(element, 'submit_answer');

    $('.ask-from-coach', element).click(function (eventObject) {
        $.ajax({
            type: "POST",
            url: askFromCoachUrl,
            data: JSON.stringify({ 'answer': studentAnswer.val() }),
            success: showCoachAnswer
        });
    });

    $('.submit-answer', element).click(function (eventObject) {
        $.ajax({
            type: "POST",
            url: submitAnswerUrl,
            data: JSON.stringify({ 'answer': studentAnswer.val() }),
            success: submitAnswer
        });
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });
}
