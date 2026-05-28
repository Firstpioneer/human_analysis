/**
 * Interview Room 模块 — 语音优先面试进行中
 */

class InterviewRoom {
  constructor() {
    this.maxFollowUps = 2;
    this._resetState();
  }

  _resetState(interviewId = null) {
    this.interviewId = interviewId;
    this.currentQuestion = null;
    this.elapsedSeconds = 0;
    this.totalDuration = 45;
    this.state = 'preparing';
    this.isInterviewEnding = false;
    this.isWaitingForAnswer = false;
    this.isSubmittingAnswer = false;
    this.answeringFollowUp = false;
    this.timerInterval = null;
    this.statusCheckAt = 0;
    this.voiceRecognition = null;
    this.recognitionSupported = false;
    this.speechSupported = false;
    this.isVoiceActive = false;
    this.shouldRestartRecognition = false;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.voices = [];
    this.userStarted = false;
    this.interviewLoaded = false;
    this.pendingStartTimer = null;
  }

  init(container, interviewId) {
    this._resetState(interviewId);

    container.innerHTML = `
      <div class="interview-room voice-interview-room" data-state="preparing">
        <div class="interview-main">
          <div class="interview-top-bar">
            <div class="interview-top-info">
              <h2 id="room-position-title">AI 面试</h2>
              <div class="info-badges">
                <span class="badge" id="badge-status">进行中</span>
                <span class="badge" id="badge-section">准备中</span>
                <span class="badge"><span id="timer-display">00:00</span> / <span id="total-time">45</span>:00</span>
              </div>
            </div>
            <div class="top-bar-actions">
              <button class="btn-end-interview" id="btn-end-interview">结束面试</button>
            </div>
          </div>

          <div class="voice-room-stage">
            <section class="ai-interviewer-card" id="ai-interviewer-card">
              <div class="ai-avatar-wrap">
                <div class="ai-avatar-ring">
                  <div class="ai-avatar-core">AI</div>
                </div>
                <div class="ai-speaking-wave" id="ai-speaking-wave" aria-hidden="true">
                  <span></span><span></span><span></span><span></span><span></span>
                </div>
              </div>
              <div class="ai-status-label" id="ai-status-label">正在准备面试</div>
              <h1 id="voice-question-title">欢迎参加 AI 面试</h1>
              <p id="voice-question-text">系统正在载入面试方案，请稍候。</p>
              <button class="voice-start-session" id="btn-start-voice-session" disabled>准备中...</button>
            </section>

            <section class="candidate-voice-card" id="candidate-voice-card">
              <div class="candidate-card-header">
                <div>
                  <h3>候选人回答区</h3>
                  <p>回答内容会被记录，但不会在面试中实时展示转写。</p>
                </div>
                <span class="candidate-state-pill" id="candidate-state-pill">等待开始</span>
              </div>

              <div class="voice-indicator" id="voice-indicator">
                <div class="waveform" aria-hidden="true"><span></span><span></span><span></span><span></span><span></span></div>
                <span id="voice-status">等待 AI 提问结束</span>
              </div>

              <div class="answer-record-status" id="answer-record-status">请听完问题后再开始回答。</div>

              <div class="voice-action-row">
                <button class="voice-primary-action" id="btn-answer-control" disabled>等待提问</button>
                <button class="voice-secondary-action" id="btn-manual-toggle" type="button">手动输入兜底</button>
              </div>

              <div class="manual-answer-panel" id="manual-answer-panel" style="display:none;">
                <textarea id="answer-input" rows="3" placeholder="仅在语音识别不可用或识别失败时使用"></textarea>
                <button class="btn-send-answer" id="btn-send-manual">提交回答</button>
              </div>

              <div class="latency-status" id="latency-status">低延迟模式：AI 说完后自动进入回答状态。</div>
            </section>
          </div>
        </div>

        <div class="interview-sidebar">
          <div class="sidebar-card">
            <h3>面试进度</h3>
            <div class="progress-bar-container"><div class="progress-bar" id="progress-bar"></div></div>
            <div class="progress-details">
              <span>已用: <strong id="elapsed-display">00:00</strong></span>
              <span>剩余: <strong id="remaining-display">45:00</strong></span>
            </div>
          </div>

          <div class="sidebar-card">
            <h3>面试方案</h3>
            <div class="plan-list" id="plan-list"></div>
          </div>

          <div class="sidebar-card" id="current-question-card">
            <h3>当前问题</h3>
            <div id="current-question-display" class="current-question"><p>等待开始...</p></div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this._initSpeech();
    this._initVoice();
    this._setState('preparing');
    this._startInterview();

    return () => this._cleanup();
  }

  _bindEvents(container) {
    container.querySelector('#btn-end-interview').addEventListener('click', () => this.endInterview());
    container.querySelector('#btn-start-voice-session').addEventListener('click', () => this._beginVoiceSession());
    container.querySelector('#btn-answer-control').addEventListener('click', () => this._handleAnswerControl());
    container.querySelector('#btn-manual-toggle').addEventListener('click', () => this._toggleManualPanel());
    container.querySelector('#btn-send-manual').addEventListener('click', () => this.sendAnswer());
    container.querySelector('#answer-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendAnswer();
      }
    });
  }

  async _startInterview() {
    try {
      const data = await api.getInterview(this.interviewId);
      if (data.success && data.interview) {
        const interview = data.interview;
        this.totalDuration = interview.plan?.total_duration_minutes || 45;

        const container = document.querySelector('.interview-room');
        if (container) {
          container.querySelector('#total-time').textContent = this.totalDuration;
          container.querySelector('#room-position-title').textContent =
            interview.candidate?.profile_ref || interview._profile?.position?.title || 'AI 面试';
          this._renderPlan(interview.plan?.sections || []);

          if (interview.status === '已完成') {
            this._showCompleted();
            return;
          }
        }

        this.startTimer();
        this.interviewLoaded = true;
        this._enableVoiceStart();
      }
    } catch (e) {
      console.error('加载面试失败:', e);
      showToast('加载面试失败: ' + e.message, 'error');
      this._setLatencyStatus('面试加载失败，请返回重试。');
    }
  }

  _renderPlan(sections) {
    const planList = document.getElementById('plan-list');
    if (!planList) return;
    if (!sections.length) {
      planList.innerHTML = '<div class="empty-hint">暂无面试方案</div>';
      return;
    }
    planList.innerHTML = sections.map(s => `
      <div class="plan-item" data-section="${this._escape(s.section_name)}">
        <div class="plan-item-header">
          <span class="plan-name">${this._escape(s.section_name)}</span>
          <span class="plan-time">${s.duration_minutes || 0}分钟</span>
        </div>
        <div class="question-count">${s.questions ? s.questions.length + ' 个问题' : '开放式环节'}</div>
      </div>
    `).join('');
  }

  _enableVoiceStart() {
    const btn = document.getElementById('btn-start-voice-session');
    if (!btn) return;
    btn.disabled = false;
    btn.textContent = this.speechSupported ? '开始语音面试' : '开始面试';
    this._setLatencyStatus(this.speechSupported ? '点击开始后浏览器会允许 AI 语音播报。' : '当前浏览器不支持语音播报，将以文字问题继续。');
  }

  _beginVoiceSession() {
    if (!this.interviewLoaded || this.userStarted || this.isInterviewEnding) return;
    this.userStarted = true;
    const btn = document.getElementById('btn-start-voice-session');
    if (btn) {
      btn.disabled = true;
      btn.textContent = '语音面试进行中';
    }
    this._primeSpeechSynthesis();
    this._setLatencyStatus('正在获取第一题。');
    this.askNextQuestion();
  }

  _primeSpeechSynthesis() {
    if (!this.speechSupported) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(' ');
      utterance.lang = 'zh-CN';
      utterance.volume = 0;
      window.speechSynthesis.speak(utterance);
      window.speechSynthesis.cancel();
    } catch (e) {}
  }

  _initSpeech() {
    this.speechSupported = 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window;
    if (!this.speechSupported) return;

    const loadVoices = () => { this.voices = window.speechSynthesis.getVoices() || []; };
    loadVoices();
    if ('onvoiceschanged' in window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }

  _initVoice() {
    this.recognitionSupported = 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
    if (!this.recognitionSupported) {
      this._setAnswerStatus('当前浏览器不支持语音识别，可使用手动输入兜底。');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.voiceRecognition = new SpeechRecognition();
    this.voiceRecognition.lang = 'zh-CN';
    this.voiceRecognition.continuous = true;
    this.voiceRecognition.interimResults = true;
    this.voiceRecognition.maxAlternatives = 1;

    this.voiceRecognition.onresult = (event) => {
      let finalTranscript = '';
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += text;
        else interimTranscript += text;
      }
      if (finalTranscript) this.finalTranscript += finalTranscript;
      this.interimTranscript = interimTranscript;
      this._setVoiceStatus('正在记录你的回答，转写内容不会实时显示。');
    };

    this.voiceRecognition.onerror = (event) => {
      if (event.error === 'not-allowed') {
        this.shouldRestartRecognition = false;
        this.isVoiceActive = false;
        this._updateVoiceUi();
        this._setAnswerStatus('麦克风权限被拒绝，请授权后重试，或使用手动输入兜底。');
        return;
      }
      if (event.error === 'no-speech' || event.error === 'aborted') return;
      this.shouldRestartRecognition = false;
      this.isVoiceActive = false;
      this._updateVoiceUi();
      this._setAnswerStatus('语音识别中断，请重新开始回答。');
    };

    this.voiceRecognition.onend = () => {
      if (this.shouldRestartRecognition && this.isVoiceActive && this.state === 'candidate_answering' && !this.isInterviewEnding) {
        try { this.voiceRecognition.start(); } catch (e) { this.isVoiceActive = false; }
      } else {
        this.isVoiceActive = false;
      }
      this._updateVoiceUi();
    };
  }

  _handleAnswerControl() {
    if (this.state !== 'candidate_answering' || this.isSubmittingAnswer) return;
    if (!this.recognitionSupported) {
      this._toggleManualPanel(true);
      return;
    }
    if (this.isVoiceActive) this._finishVoiceAnswer();
    else this._startListening(false);
  }

  _startListening(autoStart = false) {
    if (!this.voiceRecognition || this.state !== 'candidate_answering') return false;
    if (this.isVoiceActive) return true;

    this.finalTranscript = '';
    this.interimTranscript = '';
    this.isVoiceActive = true;
    this.shouldRestartRecognition = true;
    this._updateVoiceUi();
    this._setAnswerStatus('正在记录你的回答，回答结束后点击“结束回答”。');

    try {
      this.voiceRecognition.start();
      return true;
    } catch (e) {
      this.isVoiceActive = false;
      this.shouldRestartRecognition = false;
      this._updateVoiceUi();
      if (!autoStart) this._setAnswerStatus('语音识别启动失败，请稍后重试或使用手动输入兜底。');
      return false;
    }
  }

  _finishVoiceAnswer() {
    if (this.isSubmittingAnswer) return;
    this.shouldRestartRecognition = false;
    this.isVoiceActive = false;
    this._setState('ai_thinking', '正在整理你的回答');
    if (this.voiceRecognition) {
      try { this.voiceRecognition.stop(); } catch (e) {}
    }
    setTimeout(() => {
      const answer = this._getCapturedAnswer();
      if (!answer) {
        this._setState('candidate_answering');
        this._setAnswerStatus('没有识别到有效回答，请重新回答，或使用手动输入兜底。');
        return;
      }
      this._submitAnswer(answer);
    }, 250);
  }

  _getCapturedAnswer() {
    return `${this.finalTranscript}${this.interimTranscript}`.trim();
  }

  async sendAnswer() {
    if (this.state !== 'candidate_answering' || !this.currentQuestion || this.isInterviewEnding) return;
    const input = document.getElementById('answer-input');
    const answer = input?.value.trim();
    if (!answer) {
      this._setAnswerStatus('请输入回答后再提交。');
      return;
    }
    input.value = '';
    this.deactivateVoice();
    await this._submitAnswer(answer);
  }

  async _submitAnswer(answer) {
    if (!this.currentQuestion || this.isSubmittingAnswer) return;
    this.isSubmittingAnswer = true;
    this.isWaitingForAnswer = false;
    this._setState('ai_thinking', '正在判断是否需要追问');
    this._setAnswerStatus(`回答已记录，约 ${answer.length} 字。`);

    try {
      const data = await api.submitAnswer(this.currentQuestion.question_id, answer, {
        is_follow_up_answer: this.answeringFollowUp,
        elapsed_seconds: this.elapsedSeconds,
      });

      if (data.success && data.result?.follow_up) {
        const followUp = data.result.follow_up;
        try {
          await api.askFollowUp(followUp, { questionId: this.currentQuestion.question_id });
        } catch (e) {
          console.warn('保存追问失败:', e);
        }
        this.answeringFollowUp = true;
        this.isSubmittingAnswer = false;
        this._showQuestion({ ...this.currentQuestion, question_text: followUp, category: '追问' }, true);
        await this._speakQuestion(followUp, true);
      } else {
        this.answeringFollowUp = false;
        this.isSubmittingAnswer = false;
        await this.askNextQuestion();
      }
    } catch (e) {
      console.error('发送回答失败:', e);
      this.isSubmittingAnswer = false;
      this._setState('candidate_answering');
      this._setAnswerStatus('提交回答失败，请重试。');
      showToast('发送回答失败: ' + e.message, 'error');
    }
  }

  async askNextQuestion() {
    if (this.isInterviewEnding) return;
    this._setState('ai_thinking', '正在进入下一题');
    const elapsed = this.elapsedSeconds / 60;

    try {
      const data = await api.getNextQuestion(elapsed);
      if (data.success && data.question) {
        this.currentQuestion = data.question;
        this.answeringFollowUp = false;
        this._showQuestion(data.question, false);
        await this._speakQuestion(data.question.question_text, false);
      } else {
        await this.endInterview();
      }
    } catch (e) {
      if (String(e.message || '').includes('所有问题已问完') || String(e.message || '').includes('404')) {
        await this.endInterview();
        return;
      }
      console.error('获取问题失败:', e);
      this._setLatencyStatus('获取下一题失败，请稍后重试。');
    }
  }

  _showQuestion(question, isFollowUp) {
    const title = document.getElementById('voice-question-title');
    const text = document.getElementById('voice-question-text');
    if (title) title.textContent = isFollowUp ? '追问' : `${question.category || '当前问题'} · ${question.difficulty || '中等'}`;
    if (text) text.textContent = question.question_text || '';

    const display = document.getElementById('current-question-display');
    if (display) {
      display.innerHTML = '';
      const category = document.createElement('p');
      category.className = 'question-category';
      category.textContent = isFollowUp ? '追问' : `[${question.category || '问题'}] ${question.difficulty || ''}`;
      const qText = document.createElement('p');
      qText.className = 'question-text';
      qText.textContent = question.question_text || '';
      display.append(category, qText);
    }
  }

  _speakQuestion(text, isFollowUp = false) {
    this.deactivateVoice();
    this._setState('ai_speaking', isFollowUp ? 'AI 正在追问' : 'AI 正在提问');
    this._setLatencyStatus('请听问题，播报结束后再回答。');

    return new Promise((resolve) => {
      const finish = () => {
        if (this.isInterviewEnding) {
          resolve();
          return;
        }
        this._enterCandidateAnswering();
        resolve();
      };

      if (!this.speechSupported || !text) {
        this._setLatencyStatus('浏览器不支持语音播报，请阅读当前问题后回答。');
        setTimeout(finish, 400);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(this._normalizeSpeechText(text));
      utterance.lang = 'zh-CN';
      utterance.rate = 0.95;
      utterance.pitch = 1;
      utterance.volume = 1;
      const voice = this._selectVoice();
      if (voice) utterance.voice = voice;

      let resolved = false;
      const done = () => {
        if (resolved) return;
        resolved = true;
        if (this.pendingStartTimer) {
          clearTimeout(this.pendingStartTimer);
          this.pendingStartTimer = null;
        }
        finish();
      };
      utterance.onstart = () => this._setLatencyStatus('AI 正在语音播报问题。');
      utterance.onend = done;
      utterance.onerror = () => {
        this._setLatencyStatus('语音播报被浏览器拦截或不可用，请点击“重播问题”，或阅读当前问题后回答。');
        this._showReplayButton(text, isFollowUp);
        done();
      };

      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utterance);
        this.pendingStartTimer = setTimeout(() => {
          if (!resolved && !window.speechSynthesis.speaking) {
            this._setLatencyStatus('浏览器尚未开始播报，请点击“重播问题”。');
            this._showReplayButton(text, isFollowUp);
            done();
          }
        }, 1200);
      } catch (e) {
        done();
      }
    });
  }

  _showReplayButton(text, isFollowUp) {
    const existing = document.getElementById('btn-replay-question');
    if (existing) return;
    const row = document.querySelector('.voice-action-row');
    if (!row) return;
    const btn = document.createElement('button');
    btn.className = 'voice-secondary-action';
    btn.id = 'btn-replay-question';
    btn.type = 'button';
    btn.textContent = '重播问题';
    btn.addEventListener('click', () => {
      btn.remove();
      this._speakQuestion(text, isFollowUp);
    });
    row.appendChild(btn);
  }

  _selectVoice() {
    const voices = this.voices.length ? this.voices : (window.speechSynthesis?.getVoices() || []);
    const preferred = ['Xiaoxiao', 'Yaoyao', 'Yunxi', 'Google 普通话', 'Microsoft Huihui', 'Tingting'];
    for (const name of preferred) {
      const match = voices.find(v => v.name.includes(name));
      if (match) return match;
    }
    return voices.find(v => v.lang?.toLowerCase().startsWith('zh-cn')) || voices.find(v => v.lang?.toLowerCase().startsWith('zh')) || null;
  }

  _normalizeSpeechText(text) {
    return text
      .replace(/Redis/g, 'Redis')
      .replace(/Kafka/g, 'Kafka')
      .replace(/K8s/gi, 'K eight S')
      .replace(/CI\/CD/gi, 'C I C D');
  }

  _enterCandidateAnswering() {
    if (this.isInterviewEnding) return;
    this.finalTranscript = '';
    this.interimTranscript = '';
    this.isWaitingForAnswer = true;
    this._setState('candidate_answering');
    this._setLatencyStatus('现在可以回答。系统会尽量自动开启麦克风。');
    const started = this._startListening(true);
    if (!started) this._setAnswerStatus('准备好后点击“开始回答”。');
  }

  deactivateVoice() {
    this.shouldRestartRecognition = false;
    this.isVoiceActive = false;
    if (this.voiceRecognition) {
      try { this.voiceRecognition.stop(); } catch (e) {}
    }
    this._updateVoiceUi();
  }

  startTimer() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      this._updateTimerDisplay();
      this._checkTimeStatus();
    }, 1000);
  }

  _updateTimerDisplay() {
    const timeStr = this._formatSeconds(this.elapsedSeconds);
    const timerDisplay = document.getElementById('timer-display');
    const elapsedDisplay = document.getElementById('elapsed-display');
    if (timerDisplay) timerDisplay.textContent = timeStr;
    if (elapsedDisplay) elapsedDisplay.textContent = timeStr;

    const remaining = Math.max(0, this.totalDuration * 60 - this.elapsedSeconds);
    const remainingDisplay = document.getElementById('remaining-display');
    if (remainingDisplay) remainingDisplay.textContent = this._formatSeconds(remaining);

    const progress = Math.min(100, (this.elapsedSeconds / (this.totalDuration * 60)) * 100);
    const progressBar = document.getElementById('progress-bar');
    if (progressBar) {
      progressBar.style.width = progress + '%';
      if (progress > 85) progressBar.style.background = '#e74c3c';
      else if (progress > 65) progressBar.style.background = '#f39c12';
    }
  }

  async _checkTimeStatus() {
    if (this.elapsedSeconds - this.statusCheckAt < 8) return;
    this.statusCheckAt = this.elapsedSeconds;

    try {
      const data = await api.getInterviewStatus(this.elapsedSeconds / 60);
      if (data.success && data.time_status) {
        const ts = data.time_status;
        if (ts.current_section) {
          const badgeSection = document.getElementById('badge-section');
          if (badgeSection) badgeSection.textContent = ts.current_section.section_name;
          this._highlightPlanSection(ts.current_section.section_name);
        }
        if (ts.should_wrap_up && !this.isInterviewEnding) {
          this._setLatencyStatus('面试即将结束，后续问题会更偏收尾。');
        }
        if (ts.suggested_action === '紧急收尾' && !this.isInterviewEnding) {
          await this.endInterview();
        }
      }
    } catch (e) {}
  }

  _highlightPlanSection(sectionName) {
    document.querySelectorAll('.plan-item').forEach(item => {
      item.classList.toggle('active', item.dataset.section === sectionName);
    });
  }

  async endInterview() {
    if (this.isInterviewEnding) return;
    this.isInterviewEnding = true;
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.pendingStartTimer) clearTimeout(this.pendingStartTimer);
    this.deactivateVoice();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    this._setState('ai_thinking', '正在结束面试');

    try {
      const data = await api.endInterview();
      if (data.success) {
        this._showCompleted();
        this._setLatencyStatus('面试已结束，记录已保存。');
      }
    } catch (e) {
      console.error('结束面试失败:', e);
      this._showCompleted();
      this._setLatencyStatus('面试已在本地停止，但保存结束状态失败。');
    }
  }

  _showCompleted() {
    this.state = 'completed';
    this.isWaitingForAnswer = false;
    this.isVoiceActive = false;
    this._setState('completed');
    const badgeStatus = document.getElementById('badge-status');
    if (badgeStatus) {
      badgeStatus.textContent = '已完成';
      badgeStatus.style.background = '#d1fae5';
    }
    const btnEnd = document.getElementById('btn-end-interview');
    if (btnEnd) btnEnd.disabled = true;
    this._showRestartButton();
  }

  _showRestartButton() {
    const actions = document.querySelector('.top-bar-actions');
    if (actions && !document.getElementById('btn-restart-interview')) {
      const btn = document.createElement('button');
      btn.className = 'btn-restart-interview';
      btn.id = 'btn-restart-interview';
      btn.textContent = '重新开始';
      btn.onclick = () => this._restartInterview();
      actions.appendChild(btn);
    }
  }

  async _restartInterview() {
    try {
      const data = await api.restartInterview(this.interviewId);
      if (data.success) window.location.hash = '#/interview/' + data.interview.interview_id;
      else alert('重新开始失败: ' + (data.error || '未知错误'));
    } catch (e) {
      alert('网络错误: ' + e.message);
    }
  }

  _setState(state, detail = '') {
    this.state = state;
    const room = document.querySelector('.interview-room');
    const aiCard = document.getElementById('ai-interviewer-card');
    const statusLabel = document.getElementById('ai-status-label');
    const pill = document.getElementById('candidate-state-pill');
    if (room) room.dataset.state = state;
    if (aiCard) aiCard.dataset.state = state;

    const labels = {
      preparing: '正在准备面试',
      ai_speaking: detail || 'AI 正在提问',
      candidate_answering: this.isVoiceActive ? '正在记录回答' : '请开始回答',
      ai_thinking: detail || '正在整理你的回答',
      completed: '面试已完成',
    };
    if (statusLabel) statusLabel.textContent = labels[state] || '';
    if (pill) pill.textContent = labels[state] || '';
    this._updateVoiceUi();
  }

  _updateVoiceUi() {
    const btn = document.getElementById('btn-answer-control');
    const indicator = document.getElementById('voice-indicator');
    if (!btn || !indicator) return;

    indicator.classList.toggle('active', this.isVoiceActive);
    indicator.classList.toggle('hint', this.state === 'candidate_answering' && !this.isVoiceActive);

    if (this.state === 'candidate_answering') {
      btn.disabled = this.isSubmittingAnswer;
      btn.textContent = this.isVoiceActive ? '结束回答' : (this.recognitionSupported ? '开始回答' : '使用手动输入');
      if (this.isVoiceActive) this._setVoiceStatus('正在记录你的回答，转写内容不会实时显示。');
      else if (this.recognitionSupported) this._setVoiceStatus('准备好后点击开始回答。');
      else this._setVoiceStatus('当前浏览器不支持语音识别。');
    } else if (this.state === 'ai_speaking') {
      btn.disabled = true;
      btn.textContent = '请听完问题';
      this._setVoiceStatus('AI 提问期间不会开启麦克风。');
    } else if (this.state === 'ai_thinking') {
      btn.disabled = true;
      btn.textContent = '处理中';
      this._setVoiceStatus('正在生成追问或下一题。');
    } else if (this.state === 'completed') {
      btn.disabled = true;
      btn.textContent = '已完成';
      this._setVoiceStatus('面试已完成。');
    } else {
      btn.disabled = true;
      btn.textContent = '等待提问';
      this._setVoiceStatus('正在准备面试。');
    }
  }

  _toggleManualPanel(forceOpen = null) {
    const panel = document.getElementById('manual-answer-panel');
    if (!panel) return;
    const shouldOpen = forceOpen === null ? panel.style.display === 'none' : forceOpen;
    panel.style.display = shouldOpen ? 'block' : 'none';
    if (shouldOpen) document.getElementById('answer-input')?.focus();
  }

  _setVoiceStatus(text) {
    const status = document.getElementById('voice-status');
    if (status) status.textContent = text;
  }

  _setAnswerStatus(text) {
    const status = document.getElementById('answer-record-status');
    if (status) status.textContent = text;
  }

  _setLatencyStatus(text) {
    const status = document.getElementById('latency-status');
    if (status) status.textContent = text;
  }

  _formatSeconds(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }

  _escape(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  _cleanup() {
    if (this.timerInterval) clearInterval(this.timerInterval);
    if (this.pendingStartTimer) clearTimeout(this.pendingStartTimer);
    this.deactivateVoice();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

window.interviewRoom = new InterviewRoom();
