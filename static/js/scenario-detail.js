class ScenarioManager {
    constructor(scenarioId, statusUrl) {
        this.scenarioId = scenarioId;
        this.statusUrl = statusUrl;
        this.intervals = [];
        this.errorCount = 0;
        this.completionShown = false;
    }

    async init() {
        try {
            await this.updateStatus();
            const statusIntervalId = setInterval(() => this.updateStatus(), 1000);
            this.intervals.push(statusIntervalId);
            
            window.addEventListener('beforeunload', () => {
                this.intervals.forEach(interval => clearInterval(interval));
            });
        } catch (error) {
            console.error('Error in init:', error);
            this.showError();
        }
    }

    async updateStatus() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            const response = await fetch(this.statusUrl, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Status data:', data);

            if (data.status === 'error') {
                throw new Error(data.message || 'Unknown error occurred');
            }

            this.errorCount = 0;
            this.updateContainerStatus(data.container_status);
            this.updateProgress(data.progress_info);
            
            const isCompleted = data.progress_info && data.progress_info.progress >= 100;
            const hasQuiz = data.quiz_url !== null && data.quiz_url !== undefined;
            
            console.log('Completion check:', { 
                isCompleted, 
                hasQuiz, 
                completionShown: this.completionShown 
            });
            
            if (isCompleted && hasQuiz && !this.completionShown) {
                console.log('Showing quiz prompt');
                this.completionShown = true;
                
                this.intervals.forEach(interval => clearInterval(interval));
                
                await Swal.fire({
                    title: 'Scenario Completed!',
                    text: 'Please complete the quiz to finish this scenario.',
                    icon: 'success',
                    confirmButtonText: 'Take Quiz',
                    allowOutsideClick: false,
                    allowEscapeKey: false
                }).then((result) => {
                    if (result.isConfirmed) {
                        window.location.href = data.quiz_url;
                    }
                });
            }

        } catch (error) {
            console.error('Error updating status:', error);
            this.errorCount++;
            
            if (this.errorCount > 3) {
                this.intervals.forEach(interval => clearInterval(interval));
                this.showError();
                
                await Swal.fire({
                    title: 'Connection Error',
                    text: 'Failed to connect to the server. Please refresh the page.',
                    icon: 'error',
                    confirmButtonText: 'Refresh',
                    allowOutsideClick: false
                }).then((result) => {
                    if (result.isConfirmed) {
                        window.location.reload();
                    }
                });
            }
        }
    }

    updateContainerStatus(status) {
        const statusText = status.is_paused ? 'Paused' : 
                          status.is_running ? 'Running' : 
                          status.status.charAt(0).toUpperCase() + status.status.slice(1);
        
        const badgeClass = status.is_paused ? 'bg-warning' :
                          status.is_running ? 'bg-success' :
                          'bg-secondary';

        document.getElementById('containerStatus').innerHTML = 
            `<span class="badge ${badgeClass}">${statusText}</span>`;

        if (status.started_at) {
            const runtime = this.calculateRuntime(new Date(status.started_at));
            document.getElementById('containerRuntime').textContent = runtime;
        }
    }

    updateProgress(progressInfo) {
        const progress = progressInfo.progress || 0;
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        const levelDisplay = document.getElementById('levelDisplay');

        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;

        if (progressInfo.level) {
            levelDisplay.innerHTML = `<span class="badge">Level ${progressInfo.level}</span>`;
        }
    }

    calculateRuntime(startTime) {
        const diff = Math.floor((new Date() - startTime) / 1000);
        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        const seconds = diff % 60;
        
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            seconds.toString().padStart(2, '0')
        ].join(':');
    }

    showError() {
        document.getElementById('containerStatus').innerHTML = 
            '<span class="badge bg-danger">Error</span>';
        document.getElementById('containerRuntime').textContent = '--:--:--';
        document.getElementById('progressText').textContent = 'Error';
        document.getElementById('progressBar').style.width = '0%';
    }
}

window.addEventListener('load', function () {
    try {
        const statusBox = document.querySelector('.scenario_status_box');
        if (!statusBox) {
            console.error('Status box not found');
            return;
        }

        const scenarioId = statusBox.dataset.scenarioId;
        const statusUrl = statusBox.dataset.statusUrl;

        if (!scenarioId || !statusUrl) {
            console.error('Missing required data attributes');
            return;
        }

        const scenarioManager = new ScenarioManager(scenarioId, statusUrl);
        scenarioManager.init().catch(error => {
            console.error('Failed to initialize ScenarioManager:', error);
        });
    } catch (error) {
        console.error('Error in initialization:', error);
    }
});
