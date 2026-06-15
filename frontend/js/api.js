/**
 * 统一 API 客户端
 */

class ApiClient {
  constructor() {
    this.baseUrl = window.location.origin;
    this.apiKey = localStorage.getItem('deepseek_api_key') || '';
  }

  setApiKey(key) {
    this.apiKey = key;
    localStorage.setItem('deepseek_api_key', key);
  }

  getApiKey() { return this.apiKey; }
  hasApiKey() { return !!this.apiKey; }

  async _request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const config = {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    };
    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(error.detail || `请求失败: ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      if (err.message.includes('Failed to fetch')) {
        throw new Error('无法连接到后端服务，请确认后端已启动');
      }
      throw err;
    }
  }

  async _upload(path, file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${this.baseUrl}${path}`, { method: 'POST', body: formData });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `上传失败: ${response.status}`);
    }
    return await response.json();
  }

  // ---- Portrait API ----
  async chat(message, messages = [], conversationId = null, generateProfile = false) {
    return this._request('/api/portrait/chat', {
      method: 'POST',
      body: JSON.stringify({
        message, api_key: this.apiKey,
        messages: messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp || new Date().toISOString() })),
        conversation_id: conversationId, generate_profile: generateProfile,
      }),
    });
  }

  async parseJd(jdText) {
    return this._request('/api/portrait/parse-jd', {
      method: 'POST',
      body: JSON.stringify({ message: jdText, api_key: this.apiKey, messages: [] }),
    });
  }

  async generateProfile(messages, conversationId = null) {
    return this._request('/api/portrait/generate-profile', {
      method: 'POST',
      body: JSON.stringify({
        api_key: this.apiKey,
        messages: messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp || new Date().toISOString() })),
        conversation_id: conversationId,
      }),
    });
  }

  async saveProfile(profile, messages = []) {
    return this._request('/api/portrait/save-profile', {
      method: 'POST',
      body: JSON.stringify({
        profile,
        messages: messages.map(m => ({ role: m.role, content: m.content, timestamp: m.timestamp || new Date().toISOString() })),
      }),
    });
  }

  async listPortraitProfiles() { return this._request('/api/portrait/profiles'); }
  async getPortraitProfile(id) { return this._request(`/api/portrait/profiles/${id}`); }
  async listConversations() { return this._request('/api/portrait/conversations'); }
  async getConversation(id) { return this._request(`/api/portrait/conversations/${id}`); }
  async saveConversation(conversationId, messages, profileDraft = null, jobTitle = '') {
    return this._request('/api/portrait/conversations', {
      method: 'POST',
      body: JSON.stringify({ conversation_id: conversationId, messages, profile_draft: profileDraft, job_title: jobTitle }),
    });
  }
  async deleteConversation(id) { return this._request(`/api/portrait/conversations/${id}`, { method: 'DELETE' }); }

  // ---- Resume API ----
  async parseResume(file) { return this._upload('/api/resume/parse', file); }
  async listResumeResults() { return this._request('/api/resume/results'); }
  async getResumeResult(id) { return this._request(`/api/resume/results/${id}`); }
  async deleteResumeResult(id) { return this._request(`/api/resume/results/${id}`, { method: 'DELETE' }); }
  async createCareerProfile(requirementText) {
    return this._request('/api/resume/career-profiles', {
      method: 'POST',
      body: JSON.stringify({ requirement_text: requirementText }),
    });
  }
  async listCareerProfiles() { return this._request('/api/resume/career-profiles'); }
  async getCareerProfile(id) { return this._request(`/api/resume/career-profiles/${id}`); }
  async deleteCareerProfile(id) { return this._request(`/api/resume/career-profiles/${id}`, { method: 'DELETE' }); }

  // ---- Interview API ----
  async startInterview(config) {
    return this._request('/api/interview/start', { method: 'POST', body: JSON.stringify(config) });
  }
  async getNextQuestion(elapsedMinutes) {
    return this._request('/api/interview/next-question', { method: 'POST', body: JSON.stringify({ elapsed_minutes: elapsedMinutes }) });
  }
  async submitAnswer(questionId, answer, options = {}) {
    return this._request('/api/interview/answer', {
      method: 'POST',
      body: JSON.stringify({ question_id: questionId, answer, ...options })
    });
  }
  async askFollowUp(question, options = {}) {
    return this._request('/api/interview/ask-follow-up', { method: 'POST', body: JSON.stringify({ question, ...options }) });
  }
  async endInterview() {
    return this._request('/api/interview/end', { method: 'POST' });
  }
  async getInterviewStatus(elapsedMinutes) {
    return this._request('/api/interview/status', { method: 'POST', body: JSON.stringify({ elapsed_minutes: elapsedMinutes }) });
  }
  async listInterviews() { return this._request('/api/interview/list'); }
  async getInterview(id) { return this._request(`/api/interview/detail/${id}`); }
  async deleteInterview(id) { return this._request(`/api/interview/detail/${id}`, { method: 'DELETE' }); }
  async restartInterview(id) { return this._request(`/api/interview/restart/${id}`, { method: 'POST' }); }

  // ---- 语音 API (阿里云 NLS) ----
  async textToSpeech(text, voice = 'xiaoyun', format = 'wav') {
    return this._request('/api/interview/tts', {
      method: 'POST',
      body: JSON.stringify({ text, voice, format }),
    });
  }

  /**
   * 文字转语音 — 返回可直接播放的 Audio 对象
   */
  async playTTS(text, voice = 'xiaoyun') {
    const url = `${this.baseUrl}/api/interview/tts`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice }),
    });
    if (!response.ok) throw new Error('TTS 请求失败');
    const blob = await response.blob();
    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    audio.onended = () => URL.revokeObjectURL(audioUrl);
    return audio;
  }

  async speechToText(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    const response = await fetch(`${this.baseUrl}/api/interview/asr`, { method: 'POST', body: formData });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'ASR 请求失败');
    }
    return await response.json();
  }

  async getVoices() { return this._request('/api/interview/voices'); }

  // ---- Interview Profiles & Candidates ----
  async listInterviewProfiles() { return this._request('/api/interview/profiles'); }
  async createInterviewProfile(data) { return this._request('/api/interview/profiles', { method: 'POST', body: JSON.stringify(data) }); }
  async getInterviewProfile(id) { return this._request(`/api/interview/profiles/${id}`); }
  async deleteInterviewProfile(id) { return this._request(`/api/interview/profiles/${id}`, { method: 'DELETE' }); }
  async listCandidates() { return this._request('/api/interview/candidates'); }
  async createCandidate(data) { return this._request('/api/interview/candidates', { method: 'POST', body: JSON.stringify(data) }); }
  async getCandidate(id) { return this._request(`/api/interview/candidates/${id}`); }
  async deleteCandidate(id) { return this._request(`/api/interview/candidates/${id}`, { method: 'DELETE' }); }

  // ---- LLM Config ----
  async getLLMConfig() { return this._request('/api/llm/config'); }
  async updateLLMConfig(config) { return this._request('/api/llm/config', { method: 'POST', body: JSON.stringify(config) }); }
  async testLLMConnection() { return this._request('/api/llm/test', { method: 'POST' }); }
  async toggleLLM(enabled) { return this._request('/api/llm/toggle', { method: 'POST', body: JSON.stringify({ enabled }) }); }
}

const api = new ApiClient();
