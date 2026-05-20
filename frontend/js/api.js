/**
 * API 调用封装
 * DeepSeek API 由后端代理，前端只调后端接口
 */

const API_BASE = 'http://localhost:8000';

class ApiClient {
  constructor() {
    this.apiKey = localStorage.getItem('deepseek_api_key') || '';
  }

  setApiKey(key) {
    this.apiKey = key;
    localStorage.setItem('deepseek_api_key', key);
  }

  getApiKey() {
    return this.apiKey;
  }

  hasApiKey() {
    return !!this.apiKey;
  }

  async _request(path, options = {}) {
    const url = `${API_BASE}${path}`;
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
        throw new Error('无法连接到后端服务，请确认后端已启动 (localhost:8000)');
      }
      throw err;
    }
  }

  async chat(message, messages = [], conversationId = null, generateProfile = false) {
    return this._request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        api_key: this.apiKey,
        messages: messages.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || new Date().toISOString()
        })),
        conversation_id: conversationId,
        generate_profile: generateProfile,
      }),
    });
  }

  async parseJd(jdText, messages = []) {
    return this._request('/api/parse-jd', {
      method: 'POST',
      body: JSON.stringify({
        message: jdText,
        api_key: this.apiKey,
        messages: [],
      }),
    });
  }

  async generateProfile(messages, conversationId = null) {
    return this._request('/api/generate-profile', {
      method: 'POST',
      body: JSON.stringify({
        api_key: this.apiKey,
        messages: messages.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || new Date().toISOString()
        })),
        conversation_id: conversationId,
      }),
    });
  }

  async saveProfile(profile, messages = []) {
    return this._request('/api/save-profile', {
      method: 'POST',
      body: JSON.stringify({
        profile,
        messages: messages.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp || new Date().toISOString()
        })),
      }),
    });
  }

  async listProfiles() {
    return this._request('/api/profiles');
  }

  async getProfile(id) {
    return this._request(`/api/profiles/${id}`);
  }

  // ---- 对话历史 ----

  async listConversations() {
    return this._request('/api/conversations');
  }

  async getConversation(id) {
    return this._request(`/api/conversations/${id}`);
  }

  async saveConversation(conversationId, messages, profileDraft = null, jobTitle = '') {
    return this._request('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({
        conversation_id: conversationId,
        messages,
        profile_draft: profileDraft,
        job_title: jobTitle,
      }),
    });
  }

  async deleteConversation(id) {
    return this._request(`/api/conversations/${id}`, {
      method: 'DELETE',
    });
  }
}

// 全局单例
const api = new ApiClient();
