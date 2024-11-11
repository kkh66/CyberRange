document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('ratingForm');
    const scenarioRatingInputs = document.querySelectorAll('input[name="scenario_rating"]');
    const scenarioRatingError = document.getElementById('scenarioRatingError');
    const submitButton = document.getElementById('submitButton');

    submitButton.disabled = true;

    scenarioRatingInputs.forEach(input => {
        input.addEventListener('change', function () {
            const hasRating = Array.from(scenarioRatingInputs).some(input => input.checked);
            submitButton.disabled = !hasRating;
            scenarioRatingError.classList.toggle('d-none', hasRating);
        });
    });
});