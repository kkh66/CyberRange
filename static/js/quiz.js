class Quiz {
    constructor() {
        this.quizData = JSON.parse(document.getElementById('quiz-data').textContent);
        this.urls = JSON.parse(document.getElementById('url-data').textContent);
        this.currentQuestionIndex = 0;
        this.score = 0;
        this.isSubmitting = false;

        this.progressBar = document.getElementById('progress-bar');
        this.questionElement = document.getElementById('question');
        this.answersElement = document.getElementById('answers');
        this.nextButton = document.getElementById('next-btn');

        this.nextButton.addEventListener('click', () => this.handleNextQuestion());
    }

    displayQuestion() {
        const question = this.quizData[this.currentQuestionIndex];
        if (!question) return;

        this.questionElement.textContent = `Question ${this.currentQuestionIndex + 1}: ${question.question_text}`;
        this.answersElement.innerHTML = '';
        this.nextButton.style.display = 'none';

        const options = ['A', 'B', 'C', 'D'];
        question.answers.forEach((answer, index) => {
            const button = document.createElement('button');
            button.className = 'answer-btn';
            button.innerHTML = `<span class="option-label">${options[index]}</span><span class="answer-text">${answer}</span>`;
            button.addEventListener('click', () => this.selectAnswer(button, answer === question.correct_answer));
            this.answersElement.appendChild(button);
        });

        this.updateProgressBar();
    }

    updateProgressBar() {
        const progress = ((this.currentQuestionIndex + 1) / this.quizData.length) * 100;
        this.progressBar.style.width = `${progress}%`;
    }

    selectAnswer(button, isCorrect) {
        const buttons = document.querySelectorAll('.answer-btn');
        buttons.forEach(button => button.disabled = true);

        if (isCorrect) {
            button.classList.add('correct');
            this.score++;
        } else {
            button.classList.add('wrong');
            buttons.forEach(btn => {
                if (btn.querySelector('.answer-text').textContent === this.quizData[this.currentQuestionIndex].correct_answer) {
                    btn.classList.add('correct');
                }
            });
        }

        this.nextButton.style.display = 'inline-block';

        if (this.currentQuestionIndex === this.quizData.length - 1) {
            this.nextButton.textContent = 'Complete Quiz';
        }
    }

    async handleNextQuestion() {
        if (this.isSubmitting) return;

        this.currentQuestionIndex++;
        if (this.currentQuestionIndex < this.quizData.length) {
            this.displayQuestion();
        } else {
            this.isSubmitting = true;
            this.nextButton.disabled = true;
            await this.completeQuiz();
        }
    }

    async completeQuiz() {

        try {
            const loadingSwal = Swal.fire({
                title: 'Submitting Quiz...',
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            const response = await fetch(this.urls.SubmitQuiz, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    score: this.score,
                    total_questions: this.quizData.length
                })
            });

            const data = await response.json();
            await loadingSwal.close();

            if (!response.ok) {
                throw new Error(data.message || 'Failed to submit quiz results');
            }
            console.log(data);
            if (data.success) {
                const percentage = Math.round((this.score / this.quizData.length) * 100);
                const result = await Swal.fire({
                    title: 'Quiz Completed!',
                    text: `Your score: ${this.score}/${this.quizData.length} (${percentage}%)`,
                    icon: 'success',
                    confirmButtonText: 'Continue to Rating',
                    allowOutsideClick: false,
                    allowEscapeKey: false,
                    showCancelButton: false
                });

                if (result.isConfirmed && this.urls.rate_scenario) {
                    window.location.href = this.urls.rate_scenario;
                }
            }
        } catch (error) {
            console.error('Error submitting quiz results:', error);
            await Swal.fire({
                title: 'Error',
                text: error.message || 'Failed to submit quiz results',
                icon: 'error',
                confirmButtonText: 'Return to Scenario',
                allowOutsideClick: false,
                allowEscapeKey: false
            });
            if (this.urls.scenario_detail) {
                window.location.href = this.urls.scenario_detail;
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const quiz = new Quiz();
    quiz.displayQuestion();
});