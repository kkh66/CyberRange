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

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    if (!searchInput) return;

    let timeoutId;
    const delay = 300; // Debounce delay in ms

    searchInput.addEventListener('input', function(e) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            const searchTerm = e.target.value.toLowerCase();
            const contentElements = document.querySelectorAll('.base_card p, .base_card li, .level_info span');
            
            // Remove existing highlights
            document.querySelectorAll('.search_highlight').forEach(el => {
                const parent = el.parentNode;
                parent.replaceChild(document.createTextNode(el.textContent), el);
            });

            if (searchTerm.length < 2) return; // Only search for 2+ characters

            contentElements.forEach(element => {
                const text = element.textContent;
                if (!text) return;

                const regex = new RegExp(searchTerm, 'gi');
                const matches = text.match(regex);
                
                if (matches) {
                    // Highlight matches
                    let newHtml = text;
                    matches.forEach(match => {
                        newHtml = newHtml.replace(
                            match,
                            `<span class="search_highlight">${match}</span>`
                        );
                    });
                    element.innerHTML = newHtml;

                    // Scroll to first match
                    const firstHighlight = document.querySelector('.search_highlight');
                    if (firstHighlight) {
                        firstHighlight.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }
                }
            });
        }, delay);
    });
});

// Instructor list functionality
const swalCustom = Swal.mixin({
    customClass: {
        confirmButton: 'swal2-confirm',
        cancelButton: 'swal2-cancel',
        popup: 'swal2-popup'
    },
    buttonsStyling: false
});

function toggleStatus(checkbox, url) {
    const newStatus = checkbox.checked ? 'activate' : 'deactivate';

    swalCustom.fire({
        title: 'Are you sure?',
        text: `Do you want to ${newStatus} this staff member?`,
        icon: 'warning',
        showCancelButton: true,
        cancelButtonText: 'Cancel',
        confirmButtonText: 'Yes, change it!',
        background: 'rgba(33, 33, 33, 0.95)',
        reverseButtons: true,
        backdrop: `
        rgba(15, 23, 42, 0.4)
        left top
        no-repeat
    `
    }).then((result) => {
        if (result.isConfirmed) {
            // Show loading state
            swalCustom.fire({
                title: 'Processing...',
                text: 'Please wait while we update the status.',
                allowOutsideClick: false,
                showConfirmButton: false,
                willOpen: () => {
                    Swal.showLoading();
                }
            });

            // Redirect to update status
            window.location.href = url;
        } else {
            // Revert checkbox state
            checkbox.checked = !checkbox.checked;

            // Show cancelled message
            swalCustom.fire({
                title: 'Cancelled',
                text: 'Status change was cancelled',
                icon: 'info',
                timer: 1500,
                showConfirmButton: false
            });
        }
    });
}

// TinyMCE initialization
document.addEventListener('DOMContentLoaded', function() {
    tinymce.init({
        selector: '.tinymce',
        height: 300,
        plugins: 'lists ',
        toolbar: 'undo redo | formatselect | bold italic | ' +
            'alignleft aligncenter alignright alignjustify | ' +
            'bullist numlist | link',
        menubar: false,
        skin: 'oxide-dark',
        content_css: 'dark',
        promotion: false,
        statusbar: false,
        content_style: 'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 14px; color: #fff; background: #2d3748; }'
    });
});

// Form validation
document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('.needs-validation');
    if (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    }
});

