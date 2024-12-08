class ScenarioManager {
    constructor(scenarioId, statusUrl) {
        this.scenarioId = scenarioId;
        this.statusUrl = statusUrl;
        this.updateInterval = 3000;
        this.intervalId = null;
        this.runtimeIntervalId = null;
        this.currentRuntime = 0;
        this.isRunning = false;
        this.completionChecked = false;
        this.hasError = false;
        
        this.containerStatus = document.getElementById('containerStatus');
        this.levelDisplay = document.getElementById('levelDisplay');
        this.containerRuntime = document.getElementById('containerRuntime');
        this.progressBar = document.getElementById('progressBar');
        this.progressText = document.getElementById('progressText');
        
        if (this.levelDisplay) {
            this.levelDisplay.style.display = 'none';
        }
        
        if (this.containerStatus) {
            this.containerStatus.textContent = 'Not Started';
            this.containerStatus.className = 'status-badge status-stopped';
        }
        
        const statusBox = document.querySelector('.scenario_status_box');
        if (statusBox && statusBox.dataset.completed === 'true') {
            this.checkCompletionStatus();
        }
    }

    init() {
        this.updateStatus();
        this.intervalId = setInterval(() => this.updateStatus(), this.updateInterval);
        this.runtimeIntervalId = setInterval(() => this.updateRuntime(), 1000);
    }

    async updateStatus() {
        try {
            const response = await fetch(this.statusUrl);
            const data = await response.json();

            if (data.status === 'success') {
                if (data.container_status.runtime !== undefined) {
                    this.currentRuntime = data.container_status.runtime;
                }
                this.isRunning = data.container_status.is_running && !data.container_status.is_paused;
                
                this.updateUI(data);
                
                if (data.progress_info.progress >= 100 && 
                    data.container_status.status === 'completed' &&
                    !this.completionChecked) {
                    this.completionChecked = true;
                    await this.checkCompletionStatus();
                }
            }
        } catch (error) {
            if (!this.hasError) {
                this.hasError = true;
                this.showError();
            }
        }
    }

    updateRuntime() {
        if (this.isRunning) {
            this.currentRuntime++;
            this.containerRuntime.textContent = this.formatRuntime(this.currentRuntime);
        }
    }

    updateUI(data) {
        const status = data.container_status.status;
        const formattedStatus = this.formatStatus(status);
        this.containerStatus.textContent = formattedStatus;
        
        this.containerStatus.classList.forEach(className => {
            if (className.startsWith('status-')) {
                this.containerStatus.classList.remove(className);
            }
        });
        
        this.containerStatus.classList.add('status-badge', `status-${status.toLowerCase()}`);

        if (data.progress_info.level) {
            this.levelDisplay.textContent = `Level ${data.progress_info.level}`;
            this.levelDisplay.style.display = 'inline-block';
        } else {
            this.levelDisplay.style.display = 'none';
        }

        const progress = data.progress_info.progress || 0;
        this.progressBar.style.width = `${progress}%`;
        this.progressText.textContent = `${Math.round(progress)}%`;
        
        // Check need to show the screenshot dialog
        if (progress >= 100 && status === 'completed' && !this.completionChecked) {
            checkCompletion(progress);
        }
        
        const buttons = document.querySelectorAll('.control-btn');
        buttons.forEach(button => {
            const action = button.value;
            if (status === 'stopped') {
                button.style.display = action === 'start' ? 'inline-block' : 'none';
            } else if (status === 'paused') {
                button.style.display = ['unpause', 'restart', 'stop'].includes(action) ? 'inline-block' : 'none';
            } else if (status === 'running') {
                button.style.display = ['pause', 'restart', 'stop'].includes(action) ? 'inline-block' : 'none';
            } else {
                button.style.display = ['restart', 'stop'].includes(action) ? 'inline-block' : 'none';
            }
        });

        if (status === 'completed') {
            this.containerStatus.closest('.scenario_status_box').classList.add('completed');
        }
    }

    formatStatus(status) {
        const statusMap = {
            'running': 'Running',
            'paused': 'Paused',
            'completed': 'Completed',
            'error': 'Error',
            'stopped': 'Stopped'
        };
        return statusMap[status.toLowerCase()] || status;
    }

    formatRuntime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        return [hours, minutes, remainingSeconds]
            .map(v => v.toString().padStart(2, '0'))
            .join(':');
    }

    showError() {
        if (this.containerStatus) {
            this.containerStatus.textContent = 'Error';
            this.containerStatus.className = 'status-badge status-error';
        }
        if (this.progressBar) {
            this.progressBar.style.width = '0%';
            this.progressText.textContent = '0%';
        }
    }

    destroy() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
        if (this.runtimeIntervalId) {
            clearInterval(this.runtimeIntervalId);
        }
    }

    async checkCompletionStatus() {
        try {
            const statusBox = document.querySelector('.scenario_status_box');
            const isScenarioCompleted = statusBox && statusBox.dataset.completed === 'true';
            
            if (!isScenarioCompleted) {
                return;
            }

            // Check quiz completion
            const quizResponse = await fetch(`/quiz/check-completion/${this.scenarioId}/`);
            const quizData = await quizResponse.json();
            
            // Check rating completion
            const ratingResponse = await fetch(`/rate/check-completion/${this.scenarioId}/`);
            const ratingData = await ratingResponse.json();
            
            if (!quizData.completed && quizData.quiz_url) {
                window.location.href = quizData.quiz_url;
                return;
            }
            
            if (!ratingData.completed && ratingData.rating_url) {
                window.location.href = ratingData.rating_url;
                return;
            }

            if (quizData.completed && ratingData.completed) {
                await Swal.fire({
                    title: 'Scenario Completed',
                    text: 'You have already completed this scenario. Thank you for your participation!',
                    icon: 'info',
                    confirmButtonText: 'Back to Scenarios',
                    allowOutsideClick: false,
                    allowEscapeKey: false
                }).then((result) => {
                    if (result.isConfirmed) {
                        const backBtn = document.querySelector('.scenario_back_btn');
                        if (backBtn) {
                            window.location.href = backBtn.href;
                        }
                    }
                });
            }
        } catch (error) {
            console.error('Error checking completion status:', error);
        }
    }
}

function checkCompletion(progress, quizUrl) {
    if (progress >= 100) {
        const statusBox = document.querySelector('.scenario_status_box');
        if (statusBox && !statusBox.classList.contains('completed')) {
            Swal.fire({
                title: 'Congratulations!',
                text: 'Please submit screenshots as completion evidence before proceeding to the quiz.',
                icon: 'success',
                showCancelButton: true,
                confirmButtonText: 'Submit Screenshots',
                cancelButtonText: 'Later',
                allowOutsideClick: false
            }).then((result) => {
                if (result.isConfirmed) {
                    const modal = document.getElementById('screenshotModal');
                    const bootstrapModal = new bootstrap.Modal(modal);
                    bootstrapModal.show();
                }
            });
        }
    }
}

function submitScreenshots() {
    const form = document.getElementById('screenshotForm');
    const formData = new FormData();
    
    const files = document.getElementById('screenshots').files;
    
    for (let i = 0; i < files.length; i++) {
        formData.append('screenshots[]', files[i]);
    }
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    formData.append('csrfmiddlewaretoken', csrfToken);
    
    const statusBox = document.querySelector('.scenario_status_box');
    const scenarioId = statusBox.dataset.scenarioId;
    
    const submitUrl = `/scenario/submit-screenshots/${scenarioId}/`;
    
    Swal.fire({
        title: 'Uploading...',
        text: 'Please wait while we upload your screenshots',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    fetch(submitUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': csrfToken
        },
        credentials: 'same-origin'
    })
    .then(response => {
        return response.json().then(data => ({
            status: response.status,
            data: data
        }));
    })
    .then(({status, data}) => {        
        if (data.success) {
            const modal = document.getElementById('screenshotModal');
            const bootstrapModal = bootstrap.Modal.getInstance(modal);
            bootstrapModal.hide();
            
            Swal.fire({
                title: 'Success!',
                text: 'Screenshots submitted successfully',
                icon: 'success',
                confirmButtonText: 'Continue to Quiz'
            }).then((result) => {
                if (result.isConfirmed && data.quiz_url) {
                    window.location.href = data.quiz_url;
                }
            });
        } else {
            Swal.fire('Error', data.message || 'Failed to submit screenshots', 'error');
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Failed to submit screenshots. Please try again.', 'error');
    });
}

document.getElementById('screenshots').addEventListener('change', function(e) {
    const previewContainer = document.getElementById('previewContainer');
    previewContainer.innerHTML = '';
    
    Array.from(this.files).forEach(file => {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.createElement('div');
            preview.className = 'position-relative';
            preview.innerHTML = `
                <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
            `;
            previewContainer.appendChild(preview);
        }
        reader.readAsDataURL(file);
    });
});

