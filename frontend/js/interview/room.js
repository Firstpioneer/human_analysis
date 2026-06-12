/**
 * Interview Room 模块 - 纯语音面试房间
 */

class InterviewRoom {
  constructor() {
    this.interviewId = null;
    this.currentQuestion = null;
    this.elapsedSeconds = 0;
    this.timerInterval = null;
    this.ttsEnabled = true;
    this.isInterviewEnding = false;
    this.isWaitingForAnswer = false;
    this.voiceState = 'idle';
    this.mediaStream = null;
    this.audioContext = null;
    this.analyser = null;
    this.vadFrame = null;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.answerStartedAt = 0;
    this.silenceStartedAt = 0;
    this.hasDetectedSpeech = false;
    this.isMicMuted = false;
    this.activeAudio = null;
    this.totalDuration = 45;
    this.vadConfig = { speechThreshold: 0.035, silenceMs: 2500, preSpeechSilenceMs: 10000, minAnswerMs: 1200, maxAnswerMs: 300000 };
  }

  init(container, interviewId) {
    this.interviewId = interviewId;
    this.elapsedSeconds = 0;
    this.currentQuestion = null;
    this.isInterviewEnding = false;
    this.isWaitingForAnswer = false;
    this.voiceState = 'idle';

    container.innerHTML = `
      <div class="interview-room voice-interview-room" data-state="idle">
        <div class="interview-main">
          <div class="interview-top-bar voice-top-bar">
            <div class="interview-top-info">
              <h2 id="room-position-title">AI 语音面试</h2>
              <div class="info-badges">
                <span class="badge" id="badge-status">准备中</span>
                <span class="badge"><span id="timer-display">00:00</span></span>
              </div>
            </div>
            <div class="top-bar-actions">
              <button class="btn-report-view" id="btn-view-report" style="display:none;">查看报告</button>
              <button class="btn-end-interview" id="btn-end-interview">结束面试</button>
            </div>
          </div>

          <main class="voice-room-stage" aria-live="polite">
            <section class="ai-interviewer-card">
              <div class="ai-avatar-wrap">
                <div class="ai-avatar-ring"><div class="ai-avatar-core">AI</div></div>
                <div class="ai-speaking-wave" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></div>
              </div>
              <div class="ai-status-label">AI 面试官</div>
              <h1 id="voice-room-title">线上语音面试</h1>
              <p id="voice-room-status">点击开始后，面试官将通过语音与你交流。</p>
              <button class="voice-start-session" id="btn-start-voice-session">开始面试</button>
            </section>

            <section class="candidate-voice-card">
              <div class="candidate-card-header">
                <div>
                  <h3>候选人语音</h3>
                  <p id="candidate-voice-hint">等待开始</p>
                </div>
                <span class="candidate-state-pill" id="candidate-state-pill">待开始</span>
              </div>
              <div class="voice-indicator" id="voice-indicator">
                <div class="waveform"><span></span><span></span><span></span><span></span><span></span></div>
                <span id="voice-status">麦克风未启用</span>
              </div>
              <div class="answer-record-status">面试中不会显示问题或回答文本。</div>
              <div class="voice-action-row">
                <button class="voice-secondary-action" id="btn-toggle-mic" disabled>麦克风开启</button>
              </div>
            </section>
          </main>
        </div>

        <div class="interview-sidebar">
          <div class="sidebar-card">
            <h3>📊 面试进度</h3>
            <div class="progress-bar-container"><div class="progress-bar" id="progress-bar"></div></div>
            <div class="progress-details">
              <span>已用: <strong id="elapsed-display">00:00</strong></span>
              <span>剩余: <strong id="remaining-display">45:00</strong></span>
            </div>
          </div>

          <div class="sidebar-card">
            <h3>📝 面试方案</h3>
            <div class="plan-list" id="plan-list"></div>
          </div>

          <div class="sidebar-card" id="current-question-card">
            <h3>❓ 当前问题</h3>
            <div id="current-question-display" class="current-question"><p>等待开始...</p></div>
          </div>

          <div class="sidebar-card" id="follow-up-card" style="display:none;">
            <h3>💡 AI 正在思考追问...</h3>
            <div id="follow-up-display"></div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this._loadInterview();
    return () => this._cleanup();
  }

  _bindEvents(container) {
    container.querySelector('#btn-start-voice-session').addEventListener('click', () => this.startVoiceInterview());
    container.querySelector('#btn-end-interview').addEventListener('click', () => this.endInterview());
    container.querySelector('#btn-toggle-mic').addEventListener('click', () => this.toggleMic());
    container.querySelector('#btn-view-report').addEventListener('click', () => this.openReportModal());
  }

  async _loadInterview() {
    try {
      const data = await api.getInterview(this.interviewId);
      if (!data.success || !data.interview) return;
      const interview = data.interview;
      const title = interview.candidate?.profile_ref || interview._profile?.position?.title || 'AI 语音面试';
      const titleEl = document.getElementById('room-position-title');
      if (titleEl) titleEl.textContent = title;

      // 设置面试总时长
      this.totalDuration = interview._duration || 45;

      // 渲染面试方案
      this._renderPlan(interview);

      await this._checkVoiceConfig();
      if (interview.status === '已完成') {
        this._showCompleted();
        return;
      }
      this._setState('idle', '点击开始后，面试官将通过语音与你交流。', '待开始');
    } catch (e) {
      console.error('加载面试失败:', e);
      showToast('加载面试失败: ' + e.message, 'error');
    }
  }

  /** 渲染面试方案到侧边栏 */
  _renderPlan(interview) {
    const planList = document.getElementById('plan-list');
    if (!planList) return;
    const plan = interview._plan || interview.plan;
    if (!plan || !plan.sections) {
      planList.innerHTML = '<p style="color:#999;font-size:13px;">暂无面试方案</p>';
      return;
    }
    let html = '';
    for (const section of plan.sections) {
      html += `<div class="plan-section">
        <div class="plan-section-title">${this._escapeHtml(section.section_name)}</div>
        <div class="plan-section-meta">${section.question_count || ''} 题 · ${section.duration_minutes || ''} 分钟</div>
      </div>`;
    }
    planList.innerHTML = html;
  }

  async _checkVoiceConfig() {
    try {
      const data = await api.getVoices();
      this.ttsEnabled = !!data.configured;
      if (!this.ttsEnabled) this._setVoiceStatus('语音服务未配置');
    } catch (e) {
      this.ttsEnabled = false;
    }
  }

  async startVoiceInterview() {
    if (this.voiceState !== 'idle') return;
    const startBtn = document.getElementById('btn-start-voice-session');
    if (startBtn) startBtn.disabled = true;
    try {
      await this._ensureMicrophone();
      this.startTimer();
      const micBtn = document.getElementById('btn-toggle-mic');
      if (micBtn) micBtn.disabled = false;
      await this.askNextQuestion();
    } catch (e) {
      console.error('启动语音面试失败:', e);
      this._setState('idle', '无法启用麦克风，请检查浏览器权限后重试。', '麦克风异常');
      if (startBtn) startBtn.disabled = false;
      showToast('启动语音面试失败: ' + e.message, 'error');
    }
  }

  async _ensureMicrophone() {
    if (this.mediaStream) return;
    this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = this.audioContext.createMediaStreamSource(this.mediaStream);
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 1024;
    source.connect(this.analyser);
  }

  startTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds += 1;
      this._updateTimerDisplay();
      // 每 30 秒检查一次时间状态
      if (this.elapsedSeconds % 30 === 0) this._checkTimeStatus();
    }, 1000);
  }

  _updateTimerDisplay() {
    const min = Math.floor(this.elapsedSeconds / 60);
    const sec = this.elapsedSeconds % 60;
    const timeStr = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;

    const timerDisplay = document.getElementById('timer-display');
    if (timerDisplay) timerDisplay.textContent = timeStr;

    const elapsedDisplay = document.getElementById('elapsed-display');
    if (elapsedDisplay) elapsedDisplay.textContent = timeStr;

    const remaining = Math.max(0, this.totalDuration * 60 - this.elapsedSeconds);
    const rMins = Math.floor(remaining / 60);
    const rSecs = remaining % 60;
    const remainingDisplay = document.getElementById('remaining-display');
    if (remainingDisplay) remainingDisplay.textContent = `${String(rMins).padStart(2, '0')}:${String(rSecs).padStart(2, '0')}`;

    const progress = Math.min(100, (this.elapsedSeconds / (this.totalDuration * 60)) * 100);
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
      progressBar.style.width = progress + '%';
      if (progress > 85) progressBar.style.background = '#e74c3c';
      else if (progress > 65) progressBar.style.background = '#f39c12';
    }
  }

  async _checkTimeStatus() {
    const elapsed = this.elapsedSeconds / 60;
    try {
      const data = await api.getInterviewStatus(elapsed);
      if (data.success && data.time_status) {
        const ts = data.time_status;
        if (ts.should_wrap_up && !this.isInterviewEnding) {
          this._setVoiceStatus('⏰ 面试即将结束');
        }
        if (ts.suggested_action === '紧急收尾' && !this.isInterviewEnding) {
          await this.endInterview();
        }
      }
    } catch (e) {}
  }

  async askNextQuestion() {
    if (this.isInterviewEnding) return;
    this._setState('ai_thinking', '面试官正在准备下一个问题。', '等待中');
    try {
      const data = await api.getNextQuestion(this.elapsedSeconds / 60);
      if (data.success && data.question) {
        this.currentQuestion = data.question;

        // 更新侧边栏当前问题
        this._updateCurrentQuestion(data.question.question_text);

        await this._speakInterviewerText(data.question.question_text);
        if (data.question.question_id === 'WRAP_UP') {
          await this._finishAfterSpokenWrapUp();
          return;
        }
        await this._beginAnswerCapture();
      } else {
        await this._finishNaturally('今天的面试问题就到这里。感谢你的回答，接下来系统会生成本次面试反馈。');
      }
    } catch (e) {
      if (e.message && e.message.includes('所有问题已问完')) {
        await this._finishNaturally('今天的面试问题就到这里。感谢你的回答，接下来系统会生成本次面试反馈。');
        return;
      }
      console.error('获取问题失败:', e);
      this._setState('idle', '获取问题失败，请稍后重试。', '异常');
      showToast('获取下一题失败: ' + e.message, 'error');
    }
  }

  /** 更新侧边栏当前问题显示 */
  _updateCurrentQuestion(text) {
    const display = document.getElementById('current-question-display');
    if (display) display.innerHTML = `<p>${this._escapeHtml(text)}</p>`;
  }

  async _speakInterviewerText(text) {
    this._stopAnswerCapture();
    this._setState('ai_speaking', '面试官正在提问。', '请聆听');
    this._setVoiceStatus('请聆听面试官语音');
    if (!this.ttsEnabled) {
      throw new Error('语音服务未配置');
    }
    const audio = await api.playTTS(text);
    this.activeAudio = audio;
    await new Promise((resolve, reject) => {
      audio.onended = () => { this.activeAudio = null; resolve(); };
      audio.onerror = () => reject(new Error('TTS 播放失败'));
      audio.play().catch(reject);
    });
  }

  async _beginAnswerCapture() {
    if (this.isInterviewEnding || this.isMicMuted) return;
    await this._ensureMicrophone();
    this.isWaitingForAnswer = true;
    this.hasDetectedSpeech = false;
    this.answerStartedAt = 0;
    this.silenceStartedAt = performance.now();
    this.audioChunks = [];
    const recorderMimeType = this._getRecorderMimeType();
    const recorderOptions = recorderMimeType ? { mimeType: recorderMimeType } : {};
    this.mediaRecorder = new MediaRecorder(this.mediaStream, recorderOptions);
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) this.audioChunks.push(event.data);
    };
    this.mediaRecorder.onstop = () => this._handleRecordedAnswer();
    this.mediaRecorder.start();
    this._setState('candidate_ready', '请开始回答。', '等待回答');
    this._setVoiceStatus('等待你开始说话');
    this._runVadLoop();
  }

  _getRecorderMimeType() {
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) return 'audio/webm;codecs=opus';
    if (MediaRecorder.isTypeSupported('audio/webm')) return 'audio/webm';
    return '';
  }

  _runVadLoop() {
    if (!this.analyser || !this.isWaitingForAnswer) return;
    const data = new Uint8Array(this.analyser.fftSize);
    const tick = () => {
      if (!this.isWaitingForAnswer || this.isInterviewEnding) return;
      this.analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const value of data) {
        const normalized = (value - 128) / 128;
        sum += normalized * normalized;
      }
      const volume = Math.sqrt(sum / data.length);
      const now = performance.now();
      const isSpeaking = volume > this.vadConfig.speechThreshold;
      this._updateWaveform(volume, isSpeaking);
      if (isSpeaking) {
        if (!this.hasDetectedSpeech) {
          this.hasDetectedSpeech = true;
          this.answerStartedAt = now;
          this._setState('candidate_answering', '正在聆听。', '回答中');
          this._setVoiceStatus('正在聆听');
        }
        this.silenceStartedAt = 0;
      } else if (this.hasDetectedSpeech) {
        if (!this.silenceStartedAt) this.silenceStartedAt = now;
        const answerMs = now - this.answerStartedAt;
        const silenceMs = now - this.silenceStartedAt;
        if ((silenceMs >= this.vadConfig.silenceMs && answerMs >= this.vadConfig.minAnswerMs) || answerMs >= this.vadConfig.maxAnswerMs) {
          this._stopAnswerCapture();
          return;
        }
      } else if (now - this.silenceStartedAt >= this.vadConfig.preSpeechSilenceMs) {
        this._setVoiceStatus('可以直接开口回答');
        this.silenceStartedAt = now;
      }
      this.vadFrame = requestAnimationFrame(tick);
    };
    this.vadFrame = requestAnimationFrame(tick);
  }

  _stopAnswerCapture() {
    if (this.vadFrame) {
      cancelAnimationFrame(this.vadFrame);
      this.vadFrame = null;
    }
    this.isWaitingForAnswer = false;
    this._updateWaveform(0, false);
    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') this.mediaRecorder.stop();
  }

  async _handleRecordedAnswer() {
    if (this.isInterviewEnding || !this.currentQuestion) return;
    if (!this.audioChunks.length || !this.hasDetectedSpeech) {
      this.audioChunks = [];
      if (!this.isInterviewEnding) await this._beginAnswerCapture();
      return;
    }
    const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
    const audioBlob = new Blob(this.audioChunks, { type: mimeType });
    this.audioChunks = [];
    this._setState('ai_thinking', '正在整理回答。', '处理中');
    this._setVoiceStatus('正在识别语音');
    try {
      const wavBlob = await this._convertBlobToWav(audioBlob);
      const result = await api.speechToText(wavBlob, 'recording.wav');
      const answer = (result.text || '').trim();
      if (!answer) {
        await this._speakInterviewerText('我刚才没有听清你的回答，可以再说一遍吗？');
        await this._beginAnswerCapture();
        return;
      }
      if (this._isRepeatRequest(answer)) {
        await this._speakInterviewerText(this.currentQuestion.question_text);
        await this._beginAnswerCapture();
        return;
      }
      await this._submitHiddenAnswer(answer);
    } catch (e) {
      console.error('语音识别失败:', e);
      await this._speakInterviewerText('刚才的语音识别失败了，请你再回答一次。');
      await this._beginAnswerCapture();
    }
  }

  _isRepeatRequest(answer) {
    return /(?:再说一遍|重复|没听清|没听见|没明白|再讲一次|再问一次|解释一下|什么意思|什么问题)/.test(answer);
  }

  async _convertBlobToWav(audioBlob) {
    const arrayBuffer = await audioBlob.arrayBuffer();
    const decodeContext = new (window.AudioContext || window.webkitAudioContext)();
    try {
      const audioBuffer = await decodeContext.decodeAudioData(arrayBuffer);
      return this._encodeWav(audioBuffer, 16000);
    } finally {
      decodeContext.close().catch(() => {});
    }
  }

  _encodeWav(audioBuffer, targetSampleRate) {
    const source = audioBuffer.getChannelData(0);
    const sampleRate = audioBuffer.sampleRate;
    const ratio = sampleRate / targetSampleRate;
    const length = Math.floor(source.length / ratio);
    const pcm = new Int16Array(length);

    for (let i = 0; i < length; i++) {
      const sourceIndex = Math.min(Math.floor(i * ratio), source.length - 1);
      const sample = Math.max(-1, Math.min(1, source[sourceIndex]));
      pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }

    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);
    this._writeAscii(view, 0, 'RIFF');
    view.setUint32(4, 36 + pcm.length * 2, true);
    this._writeAscii(view, 8, 'WAVE');
    this._writeAscii(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, targetSampleRate, true);
    view.setUint32(28, targetSampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    this._writeAscii(view, 36, 'data');
    view.setUint32(40, pcm.length * 2, true);

    let offset = 44;
    for (let i = 0; i < pcm.length; i++, offset += 2) {
      view.setInt16(offset, pcm[i], true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }

  _writeAscii(view, offset, text) {
    for (let i = 0; i < text.length; i++) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  }

  async _submitHiddenAnswer(answer) {
    if (!this.currentQuestion || this.isInterviewEnding) return;
    const submittedQuestion = { ...this.currentQuestion };
    try {
      const data = await api.submitAnswer(submittedQuestion.question_id, answer, {
        is_follow_up_answer: !!submittedQuestion.follow_up,
        elapsed_seconds: this.elapsedSeconds,
      });
      if (!data.success || data.result?.error) throw new Error(data.result?.error || '回答提交失败');
      if (submittedQuestion.question_id === 'WRAP_UP') {
        await this._finishAfterSpokenWrapUp();
        return;
      }
      if (data.result?.follow_up) {
        // 显示追问卡片
        const followUpCard = document.getElementById('follow-up-card');
        if (followUpCard) followUpCard.style.display = 'block';

        const followUpData = await api.askFollowUp(data.result.follow_up, { question_id: submittedQuestion.question_id });
        if (followUpData.success) {
          this.currentQuestion = { ...submittedQuestion, follow_up: true, question_text: data.result.follow_up };
          this._updateCurrentQuestion(data.result.follow_up);
          await this._speakInterviewerText(data.result.follow_up);
          if (followUpCard) followUpCard.style.display = 'none';
          await this._beginAnswerCapture();
          return;
        }
        if (followUpCard) followUpCard.style.display = 'none';
      }
      await this.askNextQuestion();
    } catch (e) {
      console.error('提交回答失败:', e);
      showToast('提交回答失败: ' + e.message, 'error');
      await this._speakInterviewerText('刚才的回答提交失败，请你再回答一次。');
      await this._beginAnswerCapture();
    }
  }

  async _finishAfterSpokenWrapUp() {
    await this.endInterview('面试问答已完成，系统正在生成评估结果。', { skipConfirm: true, alreadySpoken: true });
  }

  async _finishNaturally(spokenText) {
    await this._speakInterviewerText(spokenText);
    await this.endInterview('面试问答已完成，系统正在生成评估结果。', { skipConfirm: true, alreadySpoken: true });
  }

  async endInterview(reason = '', options = {}) {
    if (this.isInterviewEnding) return;
    if (!options.skipConfirm && !window.confirm('确认结束本次面试？')) return;
    this.isInterviewEnding = true;
    if (this.timerInterval) clearInterval(this.timerInterval);
    this._stopAnswerCapture();
    this._setState('ai_thinking', reason || '正在结束面试。', '收尾中');
    try {
      if (!options.alreadySpoken && !reason) await this._speakInterviewerText('好的，本次面试到这里结束。感谢你的参与。');
      const data = await api.endInterview();
      if (data.success) {
        this._showCompleted();
        setTimeout(() => this.openReportModal(), 600);
      }
    } catch (e) {
      console.error('结束面试失败:', e);
      showToast('结束面试失败: ' + e.message, 'error');
      this.isInterviewEnding = false;
    }
  }

  toggleMic() {
    this.isMicMuted = !this.isMicMuted;
    if (this.mediaStream) this.mediaStream.getAudioTracks().forEach(track => { track.enabled = !this.isMicMuted; });
    const btn = document.getElementById('btn-toggle-mic');
    if (btn) btn.textContent = this.isMicMuted ? '麦克风关闭' : '麦克风开启';
    if (this.isMicMuted) {
      this._stopAnswerCapture();
      this._setVoiceStatus('麦克风已关闭');
    } else if (this.currentQuestion && !this.isInterviewEnding && this.voiceState !== 'ai_speaking') {
      this._beginAnswerCapture();
    }
  }

  _setState(state, statusText, candidateState) {
    this.voiceState = state;
    const room = document.querySelector('.voice-interview-room');
    if (room) room.dataset.state = state;
    const status = document.getElementById('voice-room-status');
    if (status) status.textContent = statusText || '';
    const badge = document.getElementById('badge-status');
    if (badge) badge.textContent = candidateState || statusText || '';
    const pill = document.getElementById('candidate-state-pill');
    if (pill) pill.textContent = candidateState || '';
    const hint = document.getElementById('candidate-voice-hint');
    if (hint) hint.textContent = statusText || '';
  }

  _setVoiceStatus(text) {
    const status = document.getElementById('voice-status');
    if (status) status.textContent = text;
  }

  _updateWaveform(volume, active) {
    const indicator = document.getElementById('voice-indicator');
    if (!indicator) return;
    indicator.classList.toggle('active', active);
    const bars = indicator.querySelectorAll('.waveform span');
    bars.forEach((bar, index) => {
      const boost = 1 + (index % 3) * 0.45;
      const height = Math.max(8, Math.min(34, 8 + volume * 380 * boost));
      bar.style.height = `${height}px`;
    });
  }

  _showCompleted() {
    this._setState('completed', '面试已完成，报告正在准备。', '已完成');
    this._setVoiceStatus('面试已完成');
    const endBtn = document.getElementById('btn-end-interview');
    if (endBtn) endBtn.disabled = true;
    const micBtn = document.getElementById('btn-toggle-mic');
    if (micBtn) micBtn.disabled = true;
    const startBtn = document.getElementById('btn-start-voice-session');
    if (startBtn) startBtn.style.display = 'none';
    const reportBtn = document.getElementById('btn-view-report');
    if (reportBtn) reportBtn.style.display = 'inline-flex';
  }

  async openReportModal() {
    try {
      const data = await api.getInterviewReport(this.interviewId);
      if (!data.success) throw new Error('报告加载失败');
      const report = data.report || {};
      const evaluation = data.evaluation || {};
      const overview = evaluation.overview || {};
      const overall = evaluation.overall_judgment || {};
      const dimensions = evaluation.dimension_reports || [];
      const risks = evaluation.risks || [];
      const strengths = evaluation.strengths || [];
      const weaknesses = evaluation.weaknesses || [];

      const overlay = document.createElement('div');
      overlay.className = 'report-modal-overlay';
      overlay.id = 'report-modal-overlay';
      overlay.innerHTML = `
        <div class="report-modal report-modal-v2">
          <div class="report-modal-header">
            <div class="report-modal-title-group">
              <h2>📋 面试评价报告</h2>
              <div class="report-modal-meta">
                <span>👤 ${this._escapeHtml(overview.candidate_name || '未知')}</span>
                <span>💼 ${this._escapeHtml(overview.position_title || '未知岗位')}</span>
                <span>⏱ ${overview.interview_duration_minutes || '--'} 分钟</span>
              </div>
            </div>
            <button class="report-modal-close" id="report-modal-close">×</button>
          </div>

          <div class="report-modal-body">
            <!-- 整体结论 -->
            <div class="report-v2-section report-overview-section">
              <div class="report-v2-section-header">
                <span class="report-v2-icon">🎯</span>
                <span class="report-v2-title">整体结论</span>
                <span class="report-v2-badge report-rec-${this._recClass(evaluation.recommendation)}">${this._escapeHtml(evaluation.recommendation || '待定')}</span>
              </div>
              <div class="report-overview-text">
                ${this._escapeHtml(overall.bottom_line || overview.one_line_takeaway || report.summary || evaluation.ai_comment || '暂无整体结论')}
              </div>
              ${overall.most_exciting_signal ? `<div class="report-highlight report-highlight-positive">✨ 最亮眼信号：${this._escapeHtml(overall.most_exciting_signal)}</div>` : ''}
              ${overall.most_concerning_signal ? `<div class="report-highlight report-highlight-negative">⚠️ 最大顾虑：${this._escapeHtml(overall.most_concerning_signal)}</div>` : ''}
            </div>

            <!-- 维度评估 -->
            ${dimensions.length > 0 ? `
            <div class="report-v2-section">
              <div class="report-v2-section-header">
                <span class="report-v2-icon">📊</span>
                <span class="report-v2-title">维度评估</span>
              </div>
              <div class="report-dim-grid">
                ${dimensions.map(dim => this._renderDimensionCard(dim)).join('')}
              </div>
            </div>` : ''}

            <!-- 优势 -->
            ${strengths.length > 0 ? `
            <div class="report-v2-section">
              <div class="report-v2-section-header">
                <span class="report-v2-icon">💪</span>
                <span class="report-v2-title">核心优势</span>
              </div>
              <div class="report-tag-list">
                ${strengths.map(s => `<span class="report-tag report-tag-strength">${this._escapeHtml(s)}</span>`).join('')}
              </div>
            </div>` : ''}

            <!-- 风险 -->
            ${risks.length > 0 || weaknesses.length > 0 ? `
            <div class="report-v2-section">
              <div class="report-v2-section-header">
                <span class="report-v2-icon">🚨</span>
                <span class="report-v2-title">风险信号</span>
              </div>
              ${risks.map(r => `
                <div class="report-risk-card">
                  <div class="report-risk-title">${this._escapeHtml(typeof r === 'string' ? r : (r.title || r.description || ''))}</div>
                  ${typeof r === 'object' && r.description ? `<div class="report-risk-desc">${this._escapeHtml(r.description)}</div>` : ''}
                </div>
              `).join('')}
              ${weaknesses.map(w => `
                <div class="report-risk-card report-risk-mild">
                  <div class="report-risk-title">${this._escapeHtml(w)}</div>
                </div>
              `).join('')}
            </div>` : ''}

            <!-- 综合评语 -->
            ${evaluation.ai_comment ? `
            <div class="report-v2-section">
              <div class="report-v2-section-header">
                <span class="report-v2-icon">💬</span>
                <span class="report-v2-title">综合评语</span>
              </div>
              <div class="report-comment-text">${this._escapeHtml(evaluation.ai_comment)}</div>
            </div>` : ''}
          </div>
        </div>`;
      document.body.appendChild(overlay);
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.id === 'report-modal-close') this._closeReportModal();
      });
    } catch (e) {
      console.error('报告加载失败:', e);
      showToast('整体评价报告加载失败: ' + e.message, 'error');
    }
  }

  _renderDimensionCard(dim) {
    const level = dim.signal_level || '待验证';
    const levelClass = {
      '强信号': 'signal-strong',
      '有信号': 'signal-medium',
      '待验证': 'signal-weak',
      '风险信号': 'signal-risk',
    }[level] || 'signal-weak';
    const evidence = dim.evidence || [];

    return `
      <div class="report-dim-card">
        <div class="report-dim-header">
          <span class="report-dim-name">${this._escapeHtml(dim.dimension_name || '未命名维度')}</span>
          <span class="report-dim-badge ${levelClass}">${this._escapeHtml(level)}</span>
        </div>
        ${dim.judgment ? `<div class="report-dim-judgment">${this._escapeHtml(dim.judgment)}</div>` : ''}
        ${dim.reasoning ? `<div class="report-dim-reasoning">${this._escapeHtml(dim.reasoning)}</div>` : ''}
        ${evidence.length > 0 ? `
          <div class="report-dim-evidence">
            <div class="report-dim-evidence-title">证据链</div>
            ${evidence.map(ev => `
              <div class="report-evidence-item">
                <span class="report-evidence-turn">回合 ${ev.turn_index || '?'}</span>
                <span class="report-evidence-quote">${this._escapeHtml(ev.quote || ev.content || '')}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
        ${dim.blind_spot ? `<div class="report-dim-blindspot">🕳 ${this._escapeHtml(dim.blind_spot)}</div>` : ''}
      </div>
    `;
  }

  _recClass(rec) {
    if (!rec) return 'pending';
    if (rec.includes('强烈')) return 'strong';
    if (rec.includes('推荐')) return 'good';
    if (rec.includes('不推荐')) return 'bad';
    return 'pending';
  }

  _listToText(value) {
    if (Array.isArray(value)) return value.filter(Boolean).join('；');
    if (typeof value === 'string') return value;
    return '暂无';
  }

  _closeReportModal() {
    const existing = document.getElementById('report-modal-overlay');
    if (existing) existing.remove();
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  _cleanup() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this._stopAnswerCapture();
    if (this.activeAudio) {
      this.activeAudio.pause();
      this.activeAudio = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    this._closeReportModal();
  }
}

window.interviewRoom = new InterviewRoom();
