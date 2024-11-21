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