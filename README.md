## AI Tutor XBlock

#### How to setup

1. Install in openedx
2. In both lms and cms settings, set the secret key of openai 
   ```python
    OPENAI_SECRET_KEY='set-secret-key'
   ```

#### How to use

1. In studio, add AI Coach from advanced components
2. For context field, If you want to add question and answer dynamically use this.
   For example, You have a question "What is meant by Photosynthesis"
   And student answer "photosynthesis is a process etc etc"

   Now, You can write question "context" like this:
    ```
    I've asked a question from student. Check is the student write correct answer.
    The question is {{question}}.

    The answer written by student is {{answer}}.
    ```

    Now, the `{{question}}` is replaced by your question, and the `{{answer}}` is replaced by answer before asking openai for improvements.