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
    this.mediaRecorder = null;           // 阿里云 ASR 录音器
    this.audioChunks = [];
    this.isRecording = false;
    this.mediaStream = null;             // 麦克风音频流
    this.audioContext = null;            // Web Audio 上下文
    this.audioInput = null;              // 音频输入节点
    this.audioProcessor = null;          // 音频处理节点
    this.pcmData = [];                   // PCM 音频数据
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
    // 阿里云 ASR 通过 MediaRecorder 实现，无需检查 SpeechRecognition
  }

  /** 将 Float32 PCM 数据编码为 WAV 格式的 ArrayBuffer */
  _encodeWav(samples, sampleRate) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign = numChannels * bitsPerSample / 8;
    const dataSize = samples.length * blockAlign;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);

    // WAV Header
    const writeStr = (offset, str) => { for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i)); };
    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);          // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeStr(36, 'data');
    view.setUint32(40, dataSize, true);

    // 写入 PCM 数据（Float32 → Int16）
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }
    return buffer;
  }

  /** 启动麦克风并通过 Web Audio API 采集 PCM 音频 */
  async _startRecording() {
    try {
      console.log('请求麦克风权限...');
      const mediaPromise = navigator.mediaDevices.getUserMedia({ audio: true });
      const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error('超时')), 10000));
      this.mediaStream = await Promise.race([mediaPromise, timeoutPromise]);
      console.log('麦克风已获取');
    } catch (e) {
      console.error('获取麦克风失败:', e.message);
      const status = document.getElementById('voice-status');
      if (status) status.textContent = '⚠️ 麦克风不可用';
      this.isVoiceActive = false;
      return false;
    }

    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      // Chrome 可能将 AudioContext 置于 suspended 状态，需要用户手势恢复
      if (this.audioContext.state === 'suspended') {
        await this.audioContext.resume();
      }
      console.log('AudioContext 已创建, sampleRate:', this.audioContext.sampleRate);
      this.audioInput = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.pcmData = [];
      this._vadBuffer = [];       // 当前说话段的 PCM 数据
      this._isSpeaking = false;   // 是否正在说话
      this._silenceTimer = null;  // 静默计时器
      this._vadThreshold = 0.008; // 音量阈值（更敏感，捕捉轻声说话）

      // 用 ScriptProcessorNode 采集 PCM 数据（兼容性好）
      this.audioProcessor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this.audioProcessor.onaudioprocess = (event) => {
        const channelData = event.inputBuffer.getChannelData(0);
        this.pcmData.push(new Float32Array(channelData));
        this._detectVoiceActivity(channelData);
      };

      this.audioInput.connect(this.audioProcessor);
      this.audioProcessor.connect(this.audioContext.destination);

      this.isRecording = true;
      console.log('录音已开始 (VAD 模式), 静默 2s 后自动上传');
      return true;

      // 启动定时上传：每 3 秒将 PCM 编码为 WAV 并发送到阿里云 ASR
      this._lastSendIndex = 0;
      this._asrInterval = setInterval(() => this._sendPcmChunk(), 3000);
      return true;
    } catch (e) {
      console.error('音频初始化失败:', e.message);
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
      this.isVoiceActive = false;
      return false;
    }
  }

  /** 检测语音活动：计算音量，判断说话/静默 */
  _detectVoiceActivity(channelData) {
    if (!this.isRecording || !this.isVoiceActive) return;
    // 计算 RMS 音量
    let sum = 0;
    for (let i = 0; i < channelData.length; i++) sum += channelData[i] * channelData[i];
    const rms = Math.sqrt(sum / channelData.length);

    if (rms > this._vadThreshold) {
      // 检测到声音
      if (!this._isSpeaking) {
        this._isSpeaking = true;
        const status = document.getElementById('voice-status');
        if (status) status.textContent = '🎤 说话中...';
      }
      // 声音中，清除静默计时器
      if (this._silenceTimer) { clearTimeout(this._silenceTimer); this._silenceTimer = null; }
    } else {
      if (this._isSpeaking) {
        // 之前在说话，现在安静了——启动 0.5 秒静默计时器
        if (!this._silenceTimer) {
          this._silenceTimer = setTimeout(() => {
            this._silenceTimer = null;
            this._isSpeaking = false;
            // 静默 0.5 秒，上传这一段音频
            this._sendVadChunk();
          }, 500);
        }
      }
    }
  }

  /** 将 PCM 数据重采样到 16000Hz（阿里云 ASR 最佳采样率） */
  _resampleTo16k(audioData, fromRate) {
    if (fromRate === 16000) return audioData;
    const targetRate = 16000;
    const totalSamples = Math.floor(audioData.length * targetRate / fromRate);
    const result = new Float32Array(totalSamples);
    const ratio = fromRate / targetRate;
    for (let i = 0; i < totalSamples; i++) {
      const srcIdx = i * ratio;
      const floor = Math.floor(srcIdx);
      const frac = srcIdx - floor;
      if (floor + 1 < audioData.length) {
        result[i] = audioData[floor] * (1 - frac) + audioData[floor + 1] * frac;
      } else {
        result[i] = audioData[floor];
      }
    }
    return result;
  }

  /** 归一化音频音量（放大到合适范围） */
  _normalizeAudio(audioData) {
    let maxVal = 0;
    for (let i = 0; i < audioData.length; i++) {
      const abs = Math.abs(audioData[i]);
      if (abs > maxVal) maxVal = abs;
    }
    if (maxVal < 0.001) return audioData; // 静音，不做处理
    const gain = Math.min(0.95 / maxVal, 3.0); // 最大增益 3 倍
    if (gain <= 1.0) return audioData; // 已经够大
    const result = new Float32Array(audioData.length);
    for (let i = 0; i < audioData.length; i++) result[i] = audioData[i] * gain;
    return result;
  }

  /** 上传一段说话片段到阿里云 ASR */
  async _sendVadChunk() {
    if (this.pcmData.length === 0) return;
    const originalRate = this.audioContext ? this.audioContext.sampleRate : 48000;

    // 取出当前所有 PCM 数据并清空
    const allData = this.pcmData.splice(0, this.pcmData.length);
    let totalLen = 0;
    for (const arr of allData) totalLen += arr.length;
    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const arr of allData) { merged.set(arr, offset); offset += arr.length; }

    // 重采样到 16000Hz
    const resampled = this._resampleTo16k(merged, originalRate);
    // 归一化音量
    const normalized = this._normalizeAudio(resampled);

    // 编码为 WAV（16000Hz, 16bit, mono）
    const wavBuffer = this._encodeWav(normalized, 16000);
    const wavBlob = new Blob([wavBuffer], { type: 'audio/wav' });

    try {
      const statusEl = document.getElementById('voice-status');
      if (statusEl) statusEl.textContent = '🎤 识别中...';
      const data = await api.speechToText(wavBlob);
      if (data.success && data.text) {
        const input = document.getElementById('answer-input');
        if (input) {
          const newText = data.text.trim();
          if (newText) {
            input.value = input.value ? input.value + newText : newText;
          }
        }
      }
      if (statusEl && this.isVoiceActive) statusEl.textContent = '🎤 录音中...';
    } catch (e) {
      console.warn('ASR 识别失败:', e.message);
      if (this.isVoiceActive) {
        const statusEl = document.getElementById('voice-status');
        if (statusEl) statusEl.textContent = '🎤 录音中...';
      }
    }
  }

  /** 停止录音 */
  _stopRecording() {
    this.isRecording = false;
    if (this._silenceTimer) { clearTimeout(this._silenceTimer); this._silenceTimer = null; }
    // 清空剩余的 PCM 数据，不继续识别（用户主动停止）
    this.pcmData = [];
    this._isSpeaking = false;
    // 断开音频节点
    if (this.audioProcessor) {
      this.audioProcessor.disconnect();
      this.audioProcessor = null;
    }
    if (this.audioInput) {
      this.audioInput.disconnect();
      this.audioInput = null;
    }
    if (this.audioContext) {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
    }
    // 释放麦克风
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
  }

  /** 停止录音时发送剩余 PCM 数据（已废弃，保留兼容） */
  async _transcribeAudio() {
    await this._sendVadChunk();
    const statusEl = document.getElementById('voice-status');
    if (statusEl) statusEl.textContent = '✅ 识别完成';
    setTimeout(() => { if (statusEl && !this.isVoiceActive) statusEl.textContent = '🎤 点击开始语音输入'; }, 1500);
  }

  /** 停止录音 */
  _stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
    }
  }

  /** 停止录音时发送剩余音频到阿里云 ASR */
  async _transcribeAudio() {
    console.log('_transcribeAudio 被调用, chunks:', this.audioChunks.length);
    if (this.audioChunks.length === 0) return;
    const chunks = this.audioChunks.splice(0, this.audioChunks.length);
    const mimeType = this.mediaRecorder?.mimeType || 'audio/webm';
    const audioBlob = new Blob(chunks, { type: mimeType });
    try {
      const statusEl = document.getElementById('voice-status');
      if (statusEl) statusEl.textContent = '⏳ 识别中...';
      const data = await api.speechToText(audioBlob);
      if (data.success && data.text) {
        const input = document.getElementById('answer-input');
        if (input) {
          const text = data.text.trim();
          if (text) input.value = input.value ? input.value + text : text;
        }
      }
      if (statusEl) statusEl.textContent = '✅ 识别完成';
    } catch (e) {
      console.error('ASR 请求失败:', e.message);
      const statusEl = document.getElementById('voice-status');
      if (statusEl) statusEl.textContent = '⚠️ 识别失败';
    }
  }

  toggleVoice() {
    if (this.isVoiceActive) this.deactivateVoice();
    else this.activateVoice();
  }

  async activateVoice() {
    console.log('activateVoice (阿里云 ASR)');
    this.isVoiceActive = true;
    const btn = document.getElementById('btn-voice');
    const indicator = document.getElementById('voice-indicator');
    const status = document.getElementById('voice-status');
    if (btn) btn.classList.add('active');
    if (indicator) indicator.classList.add('active');
    if (status) status.textContent = '🎤 录音中...';
    await this._startRecording();
  }

  deactivateVoice() {
    this.isVoiceActive = false;
    this._stopRecording();
    const btn = document.getElementById('btn-voice');
    const indicator = document.getElementById('voice-indicator');
    if (btn) btn.classList.remove('active');
    if (indicator) indicator.classList.remove('active');
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
        const takeaway = evaluation.overview?.one_line_takeaway
          ? `一句话判断: ${evaluation.overview.one_line_takeaway}`
          : evaluation.suitability
            ? `评估结论: ${evaluation.suitability}`
            : '';
        const recText = evaluation.recommendation
          ? `推荐结论: ${evaluation.recommendation}`
          : '';
        const commentText = evaluation.ai_comment
          ? `AI 评语: ${evaluation.ai_comment}`
          : '';
        const quality = evaluation.quality_validation?.summary;
        const qualityText = quality
          ? `质量验证: 证据链${quality.evidence_chain_health} / 稳定性${quality.stability_status} / 区分度${quality.discrimination_status}`
          : '';
        const lines = [takeaway, recText, commentText, qualityText].filter(Boolean).join('\n');
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
    this.deactivateVoice();
    // 释放麦克风（deactivateVoice 可能未完全清理）
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.isRecording = false;
    }
    if (window.speechSynthesis) window.speechSynthesis.cancel();
  }
}

window.interviewRoom = new InterviewRoom();
