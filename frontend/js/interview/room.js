/**
 * Interview Room 模块 — 面试进行中
 */

class InterviewRoom {
  constructor() {
    this.interviewId = null;
    this.currentQuestion = null;
    this.elapsedSeconds = 0;
    this.isWaitingForAnswer = false;
    this.isInterviewEnding = false;
    this.timerInterval = null;
    this.voiceRecognition = null;
    this.isVoiceActive = false;
    this.voiceEnabled = false;
    this.ttsEnabled = true;             // 阿里云 TTS 播报开关
    this.mediaRecorder = null;           // 后端 ASR 录音器
    this.audioChunks = [];
    this.isRecording = false;
    this.totalDuration = 45;
  }

  init(container, interviewId) {
    this.interviewId = interviewId;
    this.elapsedSeconds = 0;
    this.isWaitingForAnswer = false;
    this.isInterviewEnding = false;
    this.currentQuestion = null;

    container.innerHTML = `
      <div class="interview-room">
        <div class="interview-main">
          <div class="interview-top-bar">
            <div class="interview-top-info">
              <h2 id="room-position-title">AI 面试</h2>
              <div class="info-badges">
                <span class="badge" id="badge-status">🔴 进行中</span>
                <span class="badge" id="badge-section">准备中</span>
                <span class="badge">⏱ <span id="timer-display">00:00</span> / <span id="total-time">45</span>:00</span>
              </div>
            </div>
            <div class="top-bar-actions">
              <button class="btn-end-interview" id="btn-end-interview">⏹ 结束面试</button>
            </div>
          </div>

          <div class="interview-chat">
            <div class="interview-chat-messages" id="interview-messages">
              <div class="interview-msg ai-msg">
                <div class="interview-msg-avatar">🤖</div>
                <div class="interview-msg-bubble">
                  <div class="msg-header">AI 面试官</div>
                  <div class="msg-content">您好！欢迎参加本次 AI 面试。我是您的 AI 面试官，将根据您的能力和经历进行综合评估。请放松心态，如实作答。我们现在开始吧！</div>
                </div>
              </div>
            </div>
          </div>

          <div class="interview-input-area" id="interview-input-area">
            <div class="voice-indicator" id="voice-indicator">
              <div class="waveform"><span></span><span></span><span></span><span></span><span></span></div>
              <span id="voice-status">语音识别中...</span>
            </div>
            <div class="interview-input-row">
              <textarea id="answer-input" placeholder="输入您的回答...（按 Enter 发送，Shift+Enter 换行）" rows="2"></textarea>
              <div class="interview-input-actions">
                <button class="btn-voice" id="btn-voice" title="语音输入">🎤</button>
                <button class="btn-send-answer" id="btn-send">发送 →</button>
              </div>
            </div>
          </div>
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
    this._initVoice();
    this._startInterview();

    return () => {
      this._cleanup();
    };
  }

  _bindEvents(container) {
    container.querySelector('#btn-end-interview').addEventListener('click', () => this.endInterview());

    container.querySelector('#btn-send').addEventListener('click', () => this.sendAnswer());

    container.querySelector('#answer-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendAnswer();
      }
    });

    container.querySelector('#btn-voice').addEventListener('click', () => this.toggleVoice());
  }

  async _startInterview() {
    try {
      // Load interview detail to get plan info
      const data = await api.getInterview(this.interviewId);
      if (data.success && data.interview) {
        const interview = data.interview;
        this.totalDuration = interview.plan?.total_duration_minutes || 45;

        const container = document.querySelector('.interview-room');
        if (container) {
          container.querySelector('#total-time').textContent = this.totalDuration;
          container.querySelector('#room-position-title').textContent =
            interview.candidate?.profile_ref || interview._profile?.position?.title || 'AI 面试';

          // Render plan sections
          const planList = container.querySelector('#plan-list');
          if (interview.plan?.sections) {
            planList.innerHTML = interview.plan.sections.map(s => `
              <div class="plan-item" data-section="${s.section_name}">
                <div class="plan-item-header">
                  <span class="plan-name">${s.section_name}</span>
                  <span class="plan-time">${s.duration_minutes}分钟</span>
                </div>
                <div class="question-count">${s.questions ? s.questions.length + ' 个问题' : '开放式环节'}</div>
              </div>
            `).join('');
          }

          // 检查阿里云 TTS/ASR 是否已配置
          this._checkVoiceConfig();

          if (interview.status === '已完成') {
            this._showCompleted(container);
            return;
          }
        }

        this.startTimer();
        setTimeout(() => this.askNextQuestion(), 3000);
      }
    } catch (e) {
      console.error('加载面试失败:', e);
      showToast('加载面试失败: ' + e.message, 'error');
    }
  }

  async _checkVoiceConfig() {
    try {
      const data = await api.getVoices();
      if (data.success) {
        this.ttsEnabled = data.configured;
        console.log('阿里云 NLS 语音服务:', data.configured ? '已配置 ✓' : '未配置（跳过 TTS）');
      }
    } catch (e) {
      this.ttsEnabled = false;
    }
  }

  _initVoice() {
    if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) return;
    this._recreateRecognizer();
  }

  /** 创建新的 SpeechRecognition 实例（每次重新激活时重建，避免 stop 后无法重启） */
  _recreateRecognizer() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const rec = new SpeechRecognition();
    rec.lang = 'zh-CN';
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript;
        else interimTranscript += event.results[i][0].transcript;
      }
      if (finalTranscript) {
        const input = document.getElementById('answer-input');
        input.value = input.value ? input.value + finalTranscript : finalTranscript;
      }
      const status = document.getElementById('voice-status');
      if (status) status.textContent = interimTranscript ? '正在识别: ' + interimTranscript : '🎤 聆听中...';
    };

    rec.onerror = (event) => {
      if (event.error === 'not-allowed') {
        this.deactivateVoice();
        const status = document.getElementById('voice-status');
        if (status) status.textContent = '⚠️ 麦克风权限被拒绝';
        return;
      }
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      this.deactivateVoice();
    };

    rec.onend = () => {
      if (this.isVoiceActive && this.isWaitingForAnswer && !this.isInterviewEnding) {
        // 每次重新开始时重建实例，确保状态正确
        this._recreateRecognizer();
        try { this.voiceRecognition.start(); } catch (e) { this.deactivateVoice(); }
      }
    };

    this.voiceRecognition = rec;
  }

  toggleVoice() {
    if (this.isVoiceActive) this.deactivateVoice();
    else this.activateVoice();
  }

  activateVoice() {
    if (!this.voiceRecognition) {
      if (!('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
        alert('您的浏览器不支持语音识别，请使用 Chrome 浏览器');
        return;
      }
      this._recreateRecognizer();
    }
    this.isVoiceActive = true;
    const btn = document.getElementById('btn-voice');
    const indicator = document.getElementById('voice-indicator');
    const status = document.getElementById('voice-status');
    if (btn) btn.classList.add('active');
    if (indicator) indicator.classList.add('active');
    if (status) status.textContent = '🎤 聆听中...';
    try { this.voiceRecognition.start(); } catch (e) {
      // start 失败时重建实例再试一次
      console.warn('语音识别 start 失败，重建实例重试:', e.message);
      this._recreateRecognizer();
      try {
        this.voiceRecognition.start();
      } catch (e2) {
        console.error('语音识别重启失败:', e2.message);
        this.isVoiceActive = false;
        if (btn) btn.classList.remove('active');
        if (indicator) indicator.classList.remove('active');
        if (status) status.textContent = '⚠️ 启动失败';
      }
    }
  }

  deactivateVoice() {
    this.isVoiceActive = false;
    const btn = document.getElementById('btn-voice');
    const indicator = document.getElementById('voice-indicator');
    if (btn) btn.classList.remove('active');
    if (indicator) indicator.classList.remove('active');
    if (this.voiceRecognition) try { this.voiceRecognition.stop(); } catch (e) {}
  }

  startTimer() {
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      this._updateTimerDisplay();
      this._checkTimeStatus();
    }, 1000);
  }

  _updateTimerDisplay() {
    const mins = Math.floor(this.elapsedSeconds / 60);
    const secs = this.elapsedSeconds % 60;
    const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    const timerDisplay = document.getElementById('timer-display');
    const elapsedDisplay = document.getElementById('elapsed-display');
    if (timerDisplay) timerDisplay.textContent = timeStr;
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
        if (ts.current_section) {
          const badgeSection = document.getElementById('badge-section');
          if (badgeSection) badgeSection.textContent = ts.current_section.section_name;
        }
        if (ts.should_wrap_up && !this.isInterviewEnding) {
          this._addSystemMessage('⏰ 面试即将结束，请准备收尾。');
        }
        if (ts.suggested_action === '紧急收尾' && !this.isInterviewEnding) {
          await this.endInterview();
        }
      }
    } catch (e) {}
  }

  _addMessage(speaker, text, isFollowUp = false) {
    const container = document.getElementById('interview-messages');
    const div = document.createElement('div');
    const isAI = speaker === 'AI';
    div.className = `interview-msg ${isAI ? 'ai-msg' : 'candidate-msg'} ${isFollowUp ? 'follow-up' : ''}`;

    div.innerHTML = `
      <div class="interview-msg-avatar">${isAI ? '🤖' : '👤'}</div>
      <div class="interview-msg-bubble">
        <div class="msg-header">${isAI ? 'AI 面试官' : '我'}</div>
        <div class="msg-content">${text}</div>
      </div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  _addSystemMessage(text) {
    const container = document.getElementById('interview-messages');
    const div = document.createElement('div');
    div.className = 'interview-msg system-msg';
    div.innerHTML = `<div class="system-bubble">${text}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  async askNextQuestion() {
    if (this.isInterviewEnding) return;
    const elapsed = this.elapsedSeconds / 60;
    try {
      const data = await api.getNextQuestion(elapsed);
      if (data.success && data.question) {
        this.currentQuestion = data.question;
        const q = data.question;
        this._addMessage('AI', q.question_text);

        const display = document.getElementById('current-question-display');
        if (display) {
          display.innerHTML = `<p class="question-category">[${q.category}] ${q.difficulty}</p><p class="question-text">${q.question_text}</p>`;
        }

        // TTS 播报 AI 问题
        if (this.ttsEnabled) {
          this._playTTS(q.question_text);
        }

        this.isWaitingForAnswer = true;
        const input = document.getElementById('answer-input');
        if (input) input.focus();
      } else {
        await this.endInterview();
      }
    } catch (e) {
      console.error('获取问题失败:', e);
    }
  }

  // ── 阿里云 TTS 播报 ──

  async _playTTS(text) {
    try {
      const audio = await api.playTTS(text);
      const speakerIcon = document.querySelector('.interview-msg.ai-msg:last-child .msg-header');
      if (speakerIcon) {
        speakerIcon.innerHTML = 'AI 面试官 <span class="tts-indicator">🔊 播报中...</span>';
      }
      audio.onended = () => {
        const indicator = document.querySelector('.tts-indicator');
        if (indicator) indicator.remove();
      };
      audio.play().catch(e => console.warn('TTS 播放失败:', e.message));
    } catch (e) {
      console.warn('TTS 合成失败（可能未配置阿里云 NLS）:', e.message);
    }
  }

  async sendAnswer() {
    if (!this.isWaitingForAnswer || !this.currentQuestion || this.isInterviewEnding) return;
    const input = document.getElementById('answer-input');
    const answer = input.value.trim();
    if (!answer) return;

    this.isWaitingForAnswer = false;
    this._addMessage('候选人', answer);
    input.value = '';
    this.deactivateVoice();

    try {
      const data = await api.submitAnswer(this.currentQuestion.question_id, answer);

      if (data.success && data.result.follow_up) {
        const followUpCard = document.getElementById('follow-up-card');
        if (followUpCard) followUpCard.style.display = 'block';

        setTimeout(async () => {
          const followUpData = await api.askFollowUp(data.result.follow_up);
          if (followUpData.success) {
            this._addMessage('AI', data.result.follow_up, true);
            // TTS 播报追问
            if (this.ttsEnabled) {
              this._playTTS(data.result.follow_up);
            }
            this.currentQuestion = { ...this.currentQuestion, follow_up: true };
            this.isWaitingForAnswer = true;
            const inp = document.getElementById('answer-input');
            if (inp) inp.focus();
          }
          if (followUpCard) followUpCard.style.display = 'none';
        }, 1500);
      } else {
        setTimeout(() => this.askNextQuestion(), 1000);
      }
    } catch (e) {
      console.error('发送回答失败:', e);
    }
  }

  async endInterview() {
    if (this.isInterviewEnding) return;
    this.isInterviewEnding = true;
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.deactivateVoice();

    try {
      const data = await api.endInterview();
      if (data.success) {
        this._addSystemMessage('✅ 面试已结束，感谢您的参与！');
        const badgeStatus = document.getElementById('badge-status');
        if (badgeStatus) {
          badgeStatus.textContent = '✅ 已完成';
          badgeStatus.style.background = '#d1fae5';
        }
        const btnEnd = document.getElementById('btn-end-interview');
        if (btnEnd) btnEnd.disabled = true;

        this._showRestartButton();

        // 显示评估结果
        setTimeout(() => this._renderSavedDialogues(), 500);
      }
    } catch (e) {
      console.error('结束面试失败:', e);
    }

    const inputArea = document.getElementById('interview-input-area');
    if (inputArea) inputArea.style.display = 'none';
  }

  _showRestartButton() {
    const actions = document.querySelector('.top-bar-actions');
    if (actions && !document.getElementById('btn-restart-interview')) {
      const btn = document.createElement('button');
      btn.className = 'btn-restart-interview';
      btn.id = 'btn-restart-interview';
      btn.textContent = '🔄 重新开始';
      btn.onclick = () => this._restartInterview();
      actions.appendChild(btn);
    }
  }

  async _restartInterview() {
    try {
      const data = await api.restartInterview(this.interviewId);
      if (data.success) {
        window.location.hash = '#/interview/' + data.interview.interview_id;
      } else {
        alert('重新开始失败: ' + (data.error || '未知错误'));
      }
    } catch (e) {
      alert('网络错误: ' + e.message);
    }
  }

  _showCompleted(container) {
    const badgeStatus = document.getElementById('badge-status');
    if (badgeStatus) {
      badgeStatus.textContent = '✅ 已完成';
      badgeStatus.style.background = '#d1fae5';
    }
    const btnEnd = document.getElementById('btn-end-interview');
    if (btnEnd) btnEnd.style.display = 'none';
    const inputArea = document.getElementById('interview-input-area');
    if (inputArea) inputArea.style.display = 'none';
    this._showRestartButton();

    // 渲染已保存的对话记录
    this._renderSavedDialogues();
  }

  async _renderSavedDialogues() {
    try {
      const data = await api.getInterview(this.interviewId);
      if (!data.success || !data.interview) return;
      const interview = data.interview;
      const dialogues = interview.dialogues || [];
      const evaluation = interview.evaluation;

      // 检查是否已有对话记录（避免面试结束时重复渲染）
      const container = document.getElementById('interview-messages');
      const hasExistingDialogues = container && container.querySelectorAll('.candidate-msg').length > 0;
      if (!hasExistingDialogues) {
        for (const msg of dialogues) {
          this._addMessage(msg.speaker, msg.text);
        }
      }

      // 渲染评估结果
      const hasEvalMsg = container && container.querySelector('.system-msg')?.textContent.includes('面试评估');
      if (evaluation && !hasEvalMsg) {
        const scoreText = evaluation.overall_score != null
          ? `综合评分: ${evaluation.overall_score}/100`
          : '';
        const recText = evaluation.recommendation
          ? `推荐结论: ${evaluation.recommendation}`
          : '';
        const commentText = evaluation.ai_comment
          ? `AI 评语: ${evaluation.ai_comment}`
          : '';
        const lines = [scoreText, recText, commentText].filter(Boolean).join('\n');
        if (lines) {
          this._addSystemMessage('📊 面试评估\n' + lines);
        }
      }

      if (dialogues.length === 0 && !hasExistingDialogues) {
        this._addSystemMessage('此面试无对话记录');
      }
    } catch (e) {
      console.error('加载对话记录失败:', e);
    }
  }

  // ── 后端 ASR 录音 ──

  /**
   * 开始录音（使用浏览器 MediaRecorder API）
   * 录音结束后自动上传到后端阿里云 ASR 识别
   */
  async startRecording() {
    if (this.isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      this.audioChunks = [];
      this.isRecording = true;

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = async () => {
        this.isRecording = false;
        // 停止所有轨道
        stream.getTracks().forEach(t => t.stop());

        if (this.audioChunks.length === 0) return;

        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.audioChunks = [];

        // 上传到后端 ASR
        try {
          const result = await api.speechToText(audioBlob);
          if (result.success && result.text) {
            const input = document.getElementById('answer-input');
            if (input) {
              input.value = input.value ? input.value + result.text : result.text;
              // 触发输入事件
              input.dispatchEvent(new Event('input'));
            }
            const status = document.getElementById('voice-status');
            if (status) status.textContent = '✅ 识别完成: ' + result.text.substring(0, 20) + '...';
          }
        } catch (e) {
          console.warn('后端 ASR 识别失败:', e.message);
          const status = document.getElementById('voice-status');
          if (status) status.textContent = '⚠️ ASR 识别失败';
        }

        // 如果仍在激活状态，继续下一轮录音
        if (this.isVoiceActive && this.isWaitingForAnswer && !this.isInterviewEnding) {
          await this.startRecording();
        }
      };

      this.mediaRecorder.start();

      // 每 5 秒切分一次录音（持续录制）
      this._recordingInterval = setInterval(() => {
        if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
          this.mediaRecorder.stop();
          // 启动新一轮录音
          const newStream = null; // 会在 onstop 中重新获取
          // 实际上在 onstop 中会重新调用 startRecording
        }
      }, 5000);

    } catch (e) {
      console.error('启动录音失败:', e);
      this.isRecording = false;
    }
  }

  stopRecording() {
    if (this._recordingInterval) {
      clearInterval(this._recordingInterval);
      this._recordingInterval = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }
    this.isRecording = false;
  }

  _cleanup() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.stopRecording();
    this.deactivateVoice();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

window.interviewRoom = new InterviewRoom();
