//sidebar use
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

//alert for message to disappear
document.addEventListener('DOMContentLoaded', function () {
    var alerts = document.querySelectorAll('.alert');
    alerts.forEach(function (alert) {
        // Create a Bootstrap alert instance
        var bsAlert = new bootstrap.Alert(alert);

        // Set a timeout to close the alert after 5 seconds
        setTimeout(function () {
            bsAlert.close();
        }, 5000);
    });
});

//For the Add student Search Use
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

    // Format the student search results
    function formatStudent(student) {
        if (student.loading) return student.text;
        if (!student.id) return student.text;

        return $(`
            <div class="d-flex align-items-center">
                             <div class="fw-bold">${student.username || student.text}</div>          
            </div>
        `);
    }

    // Format the selected student
    function formatStudentSelection(student) {
        if (!student.id) return student.text;
        return $(`
                        <div class="d-flex align-items-center">
                            <div class="fw-bold">${student.username || student.text}</div>
                        </div>
                    `);
    }

    // Update selected students display
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

    // Clear selections when modal is closed
    $('#addStudentModal').on('hidden.bs.modal', function () {
        $('#studentSelect').val(null).trigger('change');
        $('#selectedStudents').empty();
    });
});

function copyCode() {
    const codeElement = document.getElementById('classCode');
    const copyButton = codeElement.nextElementSibling;

    navigator.clipboard.writeText(codeElement.textContent.trim())
        .then(() => {
            copyButton.classList.add('copied');
            copyButton.innerHTML = '<i class="fas fa-check"></i> Copied!';

            setTimeout(() => {
                copyButton.classList.remove('copied');
                copyButton.innerHTML = '<i class="fas fa-copy"></i> Copy';
            }, 2000);
        })
        .catch(err => {
            console.error('Failed to copy text: ', err);
        });
}

// Scenario Detail Page Functions
function initScenarioDetail(scenarioId, checkProgressUrl, containerInfoUrl) {
    function updateProgress() {
        fetch(checkProgressUrl)
            .then(response => response.json())
            .then(data => {
                const progressPercent = (data.completed / data.total) * 100;
                document.getElementById('progressBar').style.width = `${progressPercent}%`;
                document.getElementById('progressText').textContent = 
                    `${data.completed}/${data.total} steps`;

                if (data.no_steps) {
                    document.getElementById('stepDisplay').innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-info-circle fa-2x text-info mb-3"></i>
                            <h4>No Steps Available</h4>
                            <p class="text-muted">This scenario doesn't have any steps yet.</p>
                        </div>
                    `;
                } else if (data.current_step) {
                    document.getElementById('stepDisplay').innerHTML = `
                        <div class="badge bg-success mb-2">Step ${data.current_step.order + 1}</div>
                        <p class="mb-3">${data.current_step.content}</p>
                    `;
                } else if (data.completed === data.total) {
                    document.getElementById('stepDisplay').innerHTML = `
                        <div class="text-center">
                            <i class="fas fa-trophy fa-2x text-warning mb-3"></i>
                            <h4>Congratulations!</h4>
                            <p class="text-muted">You have completed all steps in this scenario.</p>
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    function updateContainerStatus() {
        fetch(containerInfoUrl)
            .then(response => response.json())
            .then(data => {
                const statusHtml = `
                    <div class="d-flex align-items-center">
                        <span class="badge ${data.status === 'running' ? 'bg-success' : 'bg-warning'} me-2">
                            ${data.status}
                        </span>
                    </div>
                `;
                document.getElementById('containerStatus').innerHTML = statusHtml;
            })
            .catch(error => {
                document.getElementById('containerStatus').innerHTML = 
                    '<div class="text-danger">Failed to load status</div>';
            });
    }

    // Initialize updates
    if (document.getElementById('stepProgress')) {
        updateProgress();
        updateContainerStatus();
        setInterval(updateProgress, 2000);
        setInterval(updateContainerStatus, 5000);
    }
}
