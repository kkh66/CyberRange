// Sidebar functionality
window.addEventListener('DOMContentLoaded', event => {
    // Toggle the side navigation
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
            document.body.classList.add('sb-sidenav-toggled');
        } else {
            document.body.classList.remove('sb-sidenav-toggled');
        }

        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.classList.toggle('sb-sidenav-toggled');
            localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
        });
    }
});

// Alert functionality
document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alerts
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        var bsAlert = new bootstrap.Alert(alert);
        setTimeout(function () {
            bsAlert.close();
        }, 5000);
    });
});

// Student search and selection
$(document).ready(function () {
    const searchUrl = $('#searchStudentsUrl').val();

    $('#studentSelect').select2({
        theme: 'bootstrap-5',
        dropdownParent: $('#addStudentModal'),
        width: '100%',
        placeholder: 'Type to search students...',
        minimumInputLength: 2,
        ajax: {
            url: searchUrl,
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term
                };
            },
            processResults: function (data) {
                return {
                    results: data.results
                };
            },
            cache: true
        },
        templateResult: formatStudent,
        templateSelection: formatStudentSelection,
        escapeMarkup: function (markup) {
            return markup;
        }
    });

    function formatStudent(student) {
        if (student.loading) return student.text;
        if (!student.id) return student.text;
        return $(`
            <div class="d-flex align-items-center">
                <div class="fw-bold">${student.username || student.text}</div>          
            </div>
        `);
    }

    function formatStudentSelection(student) {
        if (!student.id) return student.text;
        return $(`
            <div class="d-flex align-items-center">
                <div class="fw-bold">${student.username || student.text}</div>
            </div>
        `);
    }

    $('#studentSelect').on('select2:select select2:unselect', function (e) {
        updateSelectedStudents();
    });

    function updateSelectedStudents() {
        const selectedOptions = $('#studentSelect').select2('data');
        const container = $('#selectedStudents');
        container.empty();

        selectedOptions.forEach(function (student) {
            container.append(`
                <div class="alert alert-info alert-dismissible fade show" role="alert">
                    <strong>${student.username || student.text}</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `);
        });
    }

    $('#addStudentModal').on('hidden.bs.modal', function () {
        $('#studentSelect').val(null).trigger('change');
        $('#selectedStudents').empty();
    });
});

// Copy code functionality
function copyCode() {
    const codeElement = document.getElementById('classCode');
    const copyButton = codeElement.nextElementSibling;

    navigator.clipboard.writeText(codeElement.textContent.trim())
        .then(() => {
            Swal.fire({
                title: 'Copied!',
                text: 'Class code has been copied to clipboard',
                icon: 'success',
                timer: 1500,
                showConfirmButton: false,
                position: 'top-end',
                toast: true
            });
        })
        .catch(err => {
            Swal.fire({
                title: 'Error!',
                text: 'Failed to copy code',
                icon: 'error',
                timer: 1500,
                showConfirmButton: false,
                position: 'top-end',
                toast: true
            });
            console.error('Failed to copy text: ', err);
        });
}

// Time update function
function initTimeUpdate(startTimeElement, elapsedTimeElement) {
    const startTime = new Date(startTimeElement.textContent.trim());

    function updateElapsedTime() {
        const now = new Date();
        const elapsed = now - startTime;

        const hours = Math.floor(elapsed / 3600000);
        const minutes = Math.floor((elapsed % 3600000) / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);

        elapsedTimeElement.textContent =
            `${hours.toString().padStart(2, '0')}:` +
            `${minutes.toString().padStart(2, '0')}:` +
            `${seconds.toString().padStart(2, '0')}`;
    }

    // Initial update and start interval
    updateElapsedTime();
    return setInterval(updateElapsedTime, 1000);
}

function showSuggestedTimeAlert(timeLimit) {
    Swal.fire({
        title: 'Suggested Time',
        html: `<div class="text-center">
                <i class="fas fa-clock fa-2x text-info mb-3"></i>
                <p><strong>${timeLimit} minutes</strong></p>
                <p class="text-muted">Try to complete this scenario within the suggested time limit</p>
               </div>`,
        icon: 'info',
        confirmButtonText: 'Got it!',
        timer: 5000,
        timerProgressBar: true
    });
}

// Container status update function
function initContainerStatus(containerStatusElement, containerInfoUrl) {
    function updateContainerStatus() {
        fetch(containerInfoUrl)
            .then(response => response.json())
            .then(data => {
                const status = data.State?.Status?.toLowerCase() || 'unknown';
                let badgeClass = 'bg-secondary';


                switch (status) {
                    case 'running':
                        badgeClass = 'bg-success';
                        break;
                    case 'paused':
                        badgeClass = 'bg-warning';
                        break;
                    case 'exited':
                    case 'stopped':
                        badgeClass = 'bg-danger';
                        break;
                }

                const statusHtml = `
                    <div class="d-flex align-items-center">
                        <span class="badge ${badgeClass} me-2">
                            ${status.charAt(0).toUpperCase() + status.slice(1)}
                        </span>
                    </div>
                `;
                containerStatusElement.innerHTML = statusHtml;
            })
            .catch(error => {
                containerStatusElement.innerHTML =
                    '<div class="text-danger">Failed to load status</div>';
                console.error('Error:', error);
            });
    }

    // Initial update and start interval
    updateContainerStatus();
    return setInterval(updateContainerStatus, 2000);
}

// Progress update function
function initProgressUpdate(checkProgressUrl) {
    function updateProgress() {
        fetch(checkProgressUrl)
            .then(response => response.json())
            .then(data => {
                // Update progress bar
                const progressPercent = (data.completed / data.total) * 100;
                document.getElementById('progressBar').style.width = `${progressPercent}%`;
                document.getElementById('progressText').textContent =
                    `${data.completed}/${data.total} steps`;

                // Handle completion
                if (data.scenario_completed && !window.scenarioCompletionShown) {
                    window.scenarioCompletionShown = true;
                    handleScenarioCompletion(data);
                }

                // Update step display
                if (!data.scenario_completed && data.current_step) {
                    document.getElementById('stepDisplay').innerHTML = `
                        <div class="badge bg-success mb-2">Step ${data.current_step.order + 1}</div>
                        <p class="mb-3">${data.current_step.content}</p>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Initial update and start interval
    updateProgress();
    return setInterval(updateProgress, 2000);
}

// Main initialization function
function initScenarioDetail(scenarioId, checkProgressUrl, containerInfoUrl) {
    const startTimeElement = document.getElementById('startTime');
    const elapsedTimeElement = document.getElementById('elapsedTime');
    const containerStatusElement = document.getElementById('containerStatus');
    const statusBox = document.querySelector('.scenario_status_box');
    const timeLimit = statusBox.dataset.timeLimit;

    // Show suggested time alert when page loads
    if (timeLimit) {
        showSuggestedTimeAlert(timeLimit);
    }

    // Initialize all components
    const timeInterval = initTimeUpdate(startTimeElement, elapsedTimeElement);
    const statusInterval = initContainerStatus(containerStatusElement, containerInfoUrl);
    const progressInterval = initProgressUpdate(checkProgressUrl);

    // Clean up on page unload
    window.addEventListener('beforeunload', () => {
        clearInterval(timeInterval);
        clearInterval(statusInterval);
        clearInterval(progressInterval);
    });
}

// Helper function for scenario completion
function handleScenarioCompletion(data) {
    if (data.has_rated) {
        Swal.fire({
            title: 'Scenario Completed!',
            text: 'You have already rated this scenario.',
            icon: 'success',
            confirmButtonText: 'Back to List',
            confirmButtonColor: '#3085d6',
            allowOutsideClick: false,
            allowEscapeKey: false
        }).then(() => {
            window.location.href = data.list_url;
        });
    } else {
        Swal.fire({
            title: 'Congratulations!',
            text: 'You have completed all steps! Would you like to rate this scenario?',
            icon: 'success',
            showCancelButton: true,
            confirmButtonText: 'Rate Now',
            cancelButtonText: 'Back to List',
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            allowOutsideClick: false,
            allowEscapeKey: false
        }).then((result) => {
            if (result.isConfirmed) {
                window.location.href = data.completion_url;
            } else {
                window.location.href = data.list_url;
            }
        });
    }
}