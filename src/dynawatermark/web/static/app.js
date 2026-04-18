/**
 * DynaWatermark Web GUI - Frontend Application
 */

// State
const state = {
    videoFile: null,
    watermarkFile: null,
    currentStep: 1,
    jobId: null,
    ws: null
};

// DOM Elements
const elements = {
    // Drop zones
    videoDropZone: document.getElementById('videoDropZone'),
    watermarkDropZone: document.getElementById('watermarkDropZone'),
    videoInput: document.getElementById('videoInput'),
    watermarkInput: document.getElementById('watermarkInput'),
    
    // Previews
    videoPreview: document.getElementById('videoPreview'),
    watermarkPreview: document.getElementById('watermarkPreview'),
    videoName: document.getElementById('videoName'),
    videoSize: document.getElementById('videoSize'),
    watermarkName: document.getElementById('watermarkName'),
    watermarkSize: document.getElementById('watermarkSize'),
    watermarkThumb: document.getElementById('watermarkThumb'),
    
    // Buttons
    toStep2: document.getElementById('toStep2'),
    startProcess: document.getElementById('startProcess'),
    cancelJob: document.getElementById('cancelJob'),
    
    // Sliders
    maxEvents: document.getElementById('maxEvents'),
    opacityMin: document.getElementById('opacityMin'),
    opacityMax: document.getElementById('opacityMax'),
    durationMin: document.getElementById('durationMin'),
    durationMax: document.getElementById('durationMax'),
    sizeMin: document.getElementById('sizeMin'),
    sizeMax: document.getElementById('sizeMax'),
    inspectionMode: document.getElementById('inspectionMode'),
    
    // Value displays
    maxEventsValue: document.getElementById('maxEventsValue'),
    opacityValue: document.getElementById('opacityValue'),
    durationValue: document.getElementById('durationValue'),
    sizeValue: document.getElementById('sizeValue'),
    previewCount: document.getElementById('previewCount'),
    previewOpacity: document.getElementById('previewOpacity'),
    previewDuration: document.getElementById('previewDuration'),
    
    // Progress
    progressCircle: document.getElementById('progressCircle'),
    progressPercent: document.getElementById('progressPercent'),
    processStatus: document.getElementById('processStatus'),
    processMessage: document.getElementById('processMessage'),
    
    // Results
    resultMessage: document.getElementById('resultMessage'),
    downloadVideo: document.getElementById('downloadVideo'),
    downloadInspection: document.getElementById('downloadInspection'),
};

// Utility functions
const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const updateStepIndicator = (step) => {
    state.currentStep = step;
    document.querySelectorAll('.step-indicator').forEach((el, idx) => {
        if (idx + 1 === step) {
            el.classList.add('active');
            el.classList.remove('text-gray-500');
        } else if (idx + 1 < step) {
            el.classList.remove('active');
            el.classList.add('text-gray-500');
            el.innerHTML = `<i class="fas fa-check mr-2"></i>${el.textContent.trim()}`;
        } else {
            el.classList.remove('active');
            el.classList.add('text-gray-500');
        }
    });
    
    document.querySelectorAll('.step-content').forEach((el, idx) => {
        el.classList.toggle('hidden', idx + 1 !== step);
    });
};

const goToStep = (step) => {
    updateStepIndicator(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// File upload handlers
const setupDropZone = (zone, input, type) => {
    zone.addEventListener('click', () => input.click());
    
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });
    
    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });
    
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0], type);
        }
    });
    
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0], type);
        }
    });
};

const handleFile = (file, type) => {
    if (type === 'video') {
        if (!file.type.startsWith('video/')) {
            alert('請上傳影片檔案');
            return;
        }
        state.videoFile = file;
        elements.videoName.textContent = file.name;
        elements.videoSize.textContent = formatFileSize(file.size);
        elements.videoPreview.classList.remove('hidden');
        elements.videoDropZone.classList.add('hidden');
    } else {
        if (!file.type.startsWith('image/')) {
            alert('請上傳圖片檔案');
            return;
        }
        state.watermarkFile = file;
        elements.watermarkName.textContent = file.name;
        elements.watermarkSize.textContent = formatFileSize(file.size);
        elements.watermarkThumb.src = URL.createObjectURL(file);
        elements.watermarkPreview.classList.remove('hidden');
        elements.watermarkDropZone.classList.add('hidden');
    }
    
    updateNextButton();
};

const clearVideo = () => {
    state.videoFile = null;
    elements.videoFile = null;
    elements.videoPreview.classList.add('hidden');
    elements.videoDropZone.classList.remove('hidden');
    elements.videoInput.value = '';
    updateNextButton();
};

const clearWatermark = () => {
    state.watermarkFile = null;
    elements.watermarkPreview.classList.add('hidden');
    elements.watermarkDropZone.classList.remove('hidden');
    elements.watermarkInput.value = '';
    updateNextButton();
};

const updateNextButton = () => {
    elements.toStep2.disabled = !(state.videoFile && state.watermarkFile);
};

// 更新雙範圍滑桿的軌道填充視覺
const updateTrackFill = (minEl, maxEl, fillId) => {
    const fill = document.getElementById(fillId);
    if (!fill) return;
    const min = parseFloat(minEl.min);
    const max = parseFloat(minEl.max);
    const valMin = parseFloat(minEl.value);
    const valMax = parseFloat(maxEl.value);
    const leftPct = ((valMin - min) / (max - min)) * 100;
    const rightPct = ((valMax - min) / (max - min)) * 100;
    fill.style.left = `${leftPct}%`;
    fill.style.right = `${100 - rightPct}%`;
};

const updatePreview = () => {
    const maxEvents = elements.maxEvents.value;
    const opacityMin = elements.opacityMin.value;
    const opacityMax = elements.opacityMax.value;
    const durationMin = elements.durationMin.value;
    const durationMax = elements.durationMax.value;
    const sizeMin = elements.sizeMin.value;
    const sizeMax = elements.sizeMax.value;
    
    // 更新軌道填充
    updateTrackFill(elements.opacityMin, elements.opacityMax, 'opacityFill');
    updateTrackFill(elements.durationMin, elements.durationMax, 'durationFill');
    updateTrackFill(elements.sizeMin, elements.sizeMax, 'sizeFill');
    
    elements.maxEventsValue.textContent = maxEvents;
    elements.opacityValue.textContent = `${opacityMin}% - ${opacityMax}%`;
    elements.durationValue.textContent = `${durationMin}s - ${durationMax}s`;
    elements.sizeValue.textContent = `${sizeMin}% - ${sizeMax}%`;
    
    elements.previewCount.textContent = `${maxEvents} 個`;
    elements.previewOpacity.textContent = `${Math.round((parseInt(opacityMin) + parseInt(opacityMax)) / 2)}%`;
    elements.previewDuration.textContent = `${((parseFloat(durationMin) + parseFloat(durationMax)) / 2).toFixed(1)} 秒`;
};

// Slider change handlers - 簡單直接的驗證方式
const setupSliders = () => {
    elements.maxEvents.addEventListener('input', updatePreview);
    
    // 透明度範圍 - 即時驗證
    elements.opacityMin.addEventListener('input', () => {
        const min = parseInt(elements.opacityMin.value);
        const max = parseInt(elements.opacityMax.value);
        // 如果 min 超過 max，將 max 拉過來
        if (min > max) {
            elements.opacityMax.value = String(min);
        }
        updatePreview();
    });
    
    elements.opacityMax.addEventListener('input', () => {
        const min = parseInt(elements.opacityMin.value);
        const max = parseInt(elements.opacityMax.value);
        // 如果 max 低於 min，將 min 拉過來
        if (max < min) {
            elements.opacityMin.value = String(max);
        }
        updatePreview();
    });
    
    // 時間範圍 - 即時驗證
    elements.durationMin.addEventListener('input', () => {
        const min = parseFloat(elements.durationMin.value);
        const max = parseFloat(elements.durationMax.value);
        if (min > max) {
            elements.durationMax.value = String(min);
        }
        updatePreview();
    });
    
    elements.durationMax.addEventListener('input', () => {
        const min = parseFloat(elements.durationMin.value);
        const max = parseFloat(elements.durationMax.value);
        if (max < min) {
            elements.durationMin.value = String(max);
        }
        updatePreview();
    });
    
    // 尺寸範圍 - 即時驗證
    elements.sizeMin.addEventListener('input', () => {
        const min = parseInt(elements.sizeMin.value);
        const max = parseInt(elements.sizeMax.value);
        if (min > max) {
            elements.sizeMax.value = String(min);
        }
        updatePreview();
    });
    
    elements.sizeMax.addEventListener('input', () => {
        const min = parseInt(elements.sizeMin.value);
        const max = parseInt(elements.sizeMax.value);
        if (max < min) {
            elements.sizeMin.value = String(max);
        }
        updatePreview();
    });
};

// Progress update
const setProgress = (percent) => {
    const radius = 54;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percent / 100) * circumference;
    elements.progressCircle.style.strokeDashoffset = offset;
    elements.progressPercent.textContent = `${Math.round(percent)}%`;
};

// WebSocket for real-time updates
const connectWebSocket = (jobId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/jobs/${jobId}`;
    
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.error) {
            elements.processStatus.textContent = '發生錯誤';
            elements.processMessage.textContent = data.error;
            state.ws.close();
            return;
        }
        
        elements.processStatus.textContent = getStatusText(data.status);
        elements.processMessage.textContent = data.message;
        
        if (data.progress !== undefined) {
            setProgress(data.progress);
        }
        
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'canceled') {
            state.ws.close();
            if (data.status === 'completed') {
                setTimeout(() => showResults(jobId, data.message), 500);
            }
        }
    };
    
    state.ws.onerror = () => {
        // 降級為 polling
        startPolling(jobId);
    };
};

const getStatusText = (status) => {
    const map = {
        'pending': '等待中...',
        'running': '處理中...',
        'completed': '完成！',
        'failed': '失敗',
        'canceled': '已取消'
    };
    return map[status] || status;
};

const startPolling = (jobId) => {
    const poll = async () => {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            const data = await response.json();
            
            elements.processStatus.textContent = getStatusText(data.status);
            elements.processMessage.textContent = data.message;
            
            if (data.progress !== undefined) {
                setProgress(data.progress);
            }
            
            if (data.status === 'completed') {
                showResults(jobId, data.message);
            } else if (data.status !== 'running' && data.status !== 'pending') {
                // Stop polling
            } else {
                setTimeout(poll, 2000);
            }
        } catch (error) {
            console.error('Polling error:', error);
            setTimeout(poll, 5000);
        }
    };
    
    poll();
};

// Start processing
const startProcessing = async () => {
    const formData = new FormData();
    formData.append('video', state.videoFile);
    formData.append('watermark', state.watermarkFile);
    formData.append('mode', 'random');
    formData.append('max_events', elements.maxEvents.value);
    formData.append('opacity_min', elements.opacityMin.value / 100);
    formData.append('opacity_max', elements.opacityMax.value / 100);
    formData.append('duration_min', elements.durationMin.value);
    formData.append('duration_max', elements.durationMax.value);
    formData.append('size_min', elements.sizeMin.value / 100);
    formData.append('size_max', elements.sizeMax.value / 100);
    formData.append('margin_ratio', '0.03');
    formData.append('inspection', elements.inspectionMode.checked);
    
    goToStep(3);
    setProgress(0);
    
    try {
        const response = await fetch('/api/jobs', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('建立任務失敗');
        }
        
        const data = await response.json();
        state.jobId = data.job_id;
        
        // Try WebSocket first, fallback to polling
        connectWebSocket(state.jobId);
    } catch (error) {
        elements.processStatus.textContent = '錯誤';
        elements.processMessage.textContent = error.message;
    }
};

// Cancel job
const cancelJob = async () => {
    if (!state.jobId) return;
    
    try {
        await fetch(`/api/jobs/${state.jobId}`, { method: 'DELETE' });
        elements.processStatus.textContent = '已取消';
        elements.processMessage.textContent = '使用者取消處理';
        
        if (state.ws) {
            state.ws.close();
        }
        
        // 延遲後回到第一步，讓使用者看到取消確認
        setTimeout(() => {
            if (confirm('處理已取消。是否要重新開始？')) {
                // 重置狀態並回到第一步
                resetAndGoToStep1();
            }
        }, 500);
    } catch (error) {
        console.error('Cancel failed:', error);
    }
};

// 重置狀態並回到第一步
const resetAndGoToStep1 = () => {
    // 重置進度顯示
    setProgress(0);
    elements.processStatus.textContent = '準備處理...';
    elements.processMessage.textContent = '正在初始化...';
    
    // 清除任務 ID
    state.jobId = null;
    state.ws = null;
    
    // 回到第一步
    goToStep(1);
};

// Show results
const showResults = (jobId, message) => {
    goToStep(4);
    elements.resultMessage.textContent = message;
    elements.downloadVideo.href = `/api/jobs/${jobId}/download/video`;
    elements.downloadInspection.href = `/api/jobs/${jobId}/download/inspection`;
};

// Initialize
const init = () => {
    setupDropZone(elements.videoDropZone, elements.videoInput, 'video');
    setupDropZone(elements.watermarkDropZone, elements.watermarkInput, 'watermark');
    setupSliders();
    
    elements.toStep2.addEventListener('click', () => goToStep(2));
    elements.startProcess.addEventListener('click', startProcessing);
    elements.cancelJob.addEventListener('click', cancelJob);
    
    // Initial preview update
    updatePreview();
};

// Expose functions for onclick handlers
window.clearVideo = clearVideo;
window.clearWatermark = clearWatermark;
window.goToStep = goToStep;
window.resetAndGoToStep1 = resetAndGoToStep1;

// Start
document.addEventListener('DOMContentLoaded', init);
