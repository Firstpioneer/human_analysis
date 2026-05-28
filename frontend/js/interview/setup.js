/**
 * Interview 面试设置模块
 */

const LLM_PRESETS = {
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  deepseek: { base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  moonshot: { base_url: 'https://api.moonshot.cn/v1', model: 'moonshot-v1-8k' },
  custom: { base_url: '', model: '' },
};

class InterviewSetup {
  constructor() {
    this.profiles = [];
    this.candidates = [];
    this.selectedProfileId = null;
    this.selectedCandidateId = null;
  }

  init(container) {
    this.selectedProfileId = null;
    this.selectedCandidateId = null;

    container.innerHTML = `
      <div class="interview-container">
        <div class="interview-hero">
          <h1>AI 驱动的智能面试系统</h1>
          <p>选择人才画像与简历分析结果，AI 将结合岗位信号和候选人经历生成语音面试方案</p>
        </div>

        <div class="setup-card source-setup-card">
          <h2>开始一场新的面试</h2>
          <p class="card-desc">面试问题将基于人才画像输出与简历分析输出动态生成，不再使用预设岗位或技能模板</p>

          <form id="interview-form">
            <div class="source-selection-grid">
              <section class="source-card" id="portrait-source-card">
                <div class="source-card-header">
                  <div>
                    <span class="source-eyebrow">步骤 1</span>
                    <h3>选择人才画像输出</h3>
                  </div>
                  <span class="badge-count" id="profile-count">0</span>
                </div>
                <p class="source-desc">用于确定岗位目标、信号维度、必须验证项与风险画像。</p>
                <div class="saved-list source-list" id="profile-list">
                  <div class="empty-hint">正在加载画像...</div>
                </div>
                <div class="source-actions">
                  <button type="button" class="btn-test" id="btn-refresh-profiles">刷新画像</button>
                  <button type="button" class="source-empty-action" id="btn-go-portrait">去生成画像</button>
                </div>
              </section>

              <section class="source-card" id="resume-source-card">
                <div class="source-card-header">
                  <div>
                    <span class="source-eyebrow">步骤 2</span>
                    <h3>选择简历分析结果</h3>
                  </div>
                  <span class="badge-count" id="candidate-count">0</span>
                </div>
                <p class="source-desc">用于验证候选人的经历、技能声明、外部信号与简历盲点。</p>
                <div class="saved-list source-list" id="candidate-list">
                  <div class="empty-hint">正在加载简历分析结果...</div>
                </div>
                <div class="source-actions">
                  <button type="button" class="btn-test" id="btn-refresh-candidates">刷新简历</button>
                  <button type="button" class="source-empty-action" id="btn-go-resume">去解析简历</button>
                </div>
              </section>
            </div>

            <div class="form-section interview-basic-settings">
              <h3><span class="section-icon">⚙️</span> 面试设置</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>面试时长（分钟）</label>
                  <input type="number" id="duration" value="45" min="15" max="120">
                </div>
              </div>
            </div>

            <div id="selected-data-hint" class="selected-source-summary">
              请选择人才画像和简历分析结果后开始面试。
            </div>

            <button type="submit" class="btn-start-interview" id="btn-start" disabled>
              开始 AI 面试
            </button>
          </form>
        </div>

        <div class="collapse-panel">
          <div class="collapse-header" id="llm-collapse-header">
            <h3><span class="section-icon">🧠</span> 大语言模型配置</h3>
            <span class="llm-status" id="llm-status-badge">⏳ 检测中...</span>
          </div>
          <div class="collapse-body" id="llm-config-body" style="display:none;">
            <div class="llm-toggle">
              <label class="toggle-label">
                <input type="checkbox" id="llm-enabled" checked>
                <span>启用 LLM 增强模式</span>
              </label>
              <span class="toggle-hint">开启后，问题生成、追问、评估将由 AI 驱动</span>
            </div>
            <div id="llm-config-fields">
              <div class="form-group">
                <label>提供商</label>
                <select id="llm-provider">
                  <option value="openai">OpenAI</option>
                  <option value="deepseek" selected>DeepSeek</option>
                  <option value="moonshot">Moonshot（月之暗面）</option>
                  <option value="custom">自定义兼容接口</option>
                </select>
              </div>
              <div class="form-group">
                <label>API Key</label>
                <input type="password" id="llm-api-key" placeholder="sk-...">
              </div>
              <div class="form-group">
                <label>API 地址</label>
                <input type="text" id="llm-base-url" value="https://api.deepseek.com">
              </div>
              <div class="form-group">
                <label>模型名称</label>
                <input type="text" id="llm-model" value="deepseek-chat">
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label>温度 (0-2)</label>
                  <input type="number" id="llm-temperature" value="0.7" min="0" max="2" step="0.1">
                </div>
                <div class="form-group">
                  <label>最大 Token</label>
                  <input type="number" id="llm-max-tokens" value="2048" min="256" max="8192" step="256">
                </div>
              </div>
              <div class="llm-actions">
                <button type="button" class="btn-test" id="btn-test-llm">🔌 测试连接</button>
                <button type="button" class="btn-save-config" id="btn-save-llm">💾 保存配置</button>
              </div>
              <div id="llm-test-result" class="llm-test-result"></div>
            </div>
          </div>
        </div>
      </div>
    `;

    this._bindEvents(container);
    this._loadLLMConfig();
    this._loadProfiles();
    this._loadCandidates();

    return () => {};
  }

  _bindEvents(container) {
    container.querySelector('#btn-refresh-profiles').addEventListener('click', () => this._loadProfiles());
    container.querySelector('#btn-refresh-candidates').addEventListener('click', () => this._loadCandidates());
    container.querySelector('#btn-go-portrait').addEventListener('click', () => { window.location.hash = '#/portrait'; });
    container.querySelector('#btn-go-resume').addEventListener('click', () => { window.location.hash = '#/resume'; });

    container.querySelector('#llm-collapse-header').addEventListener('click', () => {
      const body = container.querySelector('#llm-config-body');
      body.style.display = body.style.display === 'none' ? 'block' : 'none';
    });

    container.querySelector('#llm-provider').addEventListener('change', () => {
      const provider = container.querySelector('#llm-provider').value;
      const preset = LLM_PRESETS[provider];
      if (preset) {
        if (preset.base_url) container.querySelector('#llm-base-url').value = preset.base_url;
        if (preset.model) container.querySelector('#llm-model').value = preset.model;
      }
    });

    container.querySelector('#llm-enabled').addEventListener('change', async () => {
      const enabled = container.querySelector('#llm-enabled').checked;
      try {
        await api.toggleLLM(enabled);
        container.querySelector('#llm-config-fields').style.opacity = enabled ? '1' : '0.5';
        this._updateLLMStatus(container, enabled, enabled ? '🧠 LLM 已启用' : '⚠️ LLM 已禁用');
      } catch (e) { console.error('切换 LLM 失败:', e); }
    });

    container.querySelector('#btn-test-llm').addEventListener('click', () => this._testLLM(container));
    container.querySelector('#btn-save-llm').addEventListener('click', () => this._saveLLMConfig(container));

    container.querySelector('#interview-form').addEventListener('submit', (e) => {
      e.preventDefault();
      this._startInterview(container);
    });
  }

  async _loadLLMConfig() {
    try {
      const data = await api.getLLMConfig();
      if (data.success) {
        const cfg = data.config;
        const container = document.querySelector('.interview-container');
        if (!container) return;

        container.querySelector('#llm-enabled').checked = cfg.available;
        container.querySelector('#llm-api-key').value = cfg.api_key || '';
        container.querySelector('#llm-base-url').value = cfg.base_url || '';
        container.querySelector('#llm-model').value = cfg.model || '';
        container.querySelector('#llm-temperature').value = cfg.temperature || 0.7;
        container.querySelector('#llm-max-tokens').value = cfg.max_tokens || 2048;

        let provider = 'custom';
        for (const [key, preset] of Object.entries(LLM_PRESETS)) {
          if (preset.base_url && cfg.base_url?.includes(preset.base_url.split('//')[1]?.split('/')[0])) {
            provider = key;
            break;
          }
        }
        container.querySelector('#llm-provider').value = provider;
        this._updateLLMStatus(container, cfg.available, cfg.available ? '🧠 LLM 已就绪' : '⚠️ LLM 未配置');
      }
    } catch (e) {
      const container = document.querySelector('.interview-container');
      if (container) this._updateLLMStatus(container, false, '❌ 加载失败');
    }
  }

  _updateLLMStatus(container, available, text) {
    const badge = container.querySelector('#llm-status-badge');
    if (badge) {
      badge.textContent = text;
      badge.className = 'llm-status ' + (available ? 'status-ok' : 'status-off');
    }
  }

  async _testLLM(container) {
    const btn = container.querySelector('#btn-test-llm');
    const result = container.querySelector('#llm-test-result');
    btn.disabled = true;
    btn.textContent = '⏳ 测试中...';
    result.className = 'llm-test-result';
    result.textContent = '';

    await this._saveLLMConfigSilent(container);

    try {
      const data = await api.testLLMConnection();
      if (data.success) {
        result.className = 'llm-test-result success';
        result.textContent = '✅ 连接成功！回复: ' + data.reply;
      } else {
        result.className = 'llm-test-result error';
        result.textContent = '❌ ' + (data.error || '连接失败');
      }
    } catch (e) {
      result.className = 'llm-test-result error';
      result.textContent = '❌ 网络错误: ' + e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = '🔌 测试连接';
    }
  }

  async _saveLLMConfig(container) {
    const result = container.querySelector('#llm-test-result');
    result.className = 'llm-test-result';
    result.textContent = '⏳ 保存中...';
    const success = await this._saveLLMConfigSilent(container);
    if (success) {
      result.className = 'llm-test-result success';
      result.textContent = '✅ 配置已保存';
      this._updateLLMStatus(container, true, '🧠 LLM 已就绪');
    } else {
      result.className = 'llm-test-result error';
      result.textContent = '❌ 保存失败';
    }
  }

  async _saveLLMConfigSilent(container) {
    try {
      const data = await api.updateLLMConfig({
        api_key: container.querySelector('#llm-api-key').value,
        base_url: container.querySelector('#llm-base-url').value,
        model: container.querySelector('#llm-model').value,
        provider: container.querySelector('#llm-provider').value,
        temperature: parseFloat(container.querySelector('#llm-temperature').value) || 0.7,
        max_tokens: parseInt(container.querySelector('#llm-max-tokens').value) || 2048,
      });
      return data.success;
    } catch (e) { return false; }
  }

  async _loadProfiles() {
    try {
      const data = await api.listInterviewProfiles();
      const container = document.querySelector('.interview-container');
      if (!container) return;

      const list = container.querySelector('#profile-list');
      const count = container.querySelector('#profile-count');
      this.profiles = data.success ? data.profiles : [];
      if (this.profiles.length) {
        count.textContent = this.profiles.length;
        list.innerHTML = this.profiles.map(p => this._renderProfileItem(p)).join('');
        if (this.selectedProfileId) {
          const target = list.querySelector(`[data-id="${this.selectedProfileId}"]`);
          if (target) target.classList.add('selected');
        }
      } else {
        count.textContent = '0';
        list.innerHTML = `
          <div class="source-empty-state">
            <strong>暂无可用画像</strong>
            <span>请先在人才画像页生成并保存画像。</span>
          </div>
        `;
      }
      this._updateSelectedHint(container);
    } catch (e) { console.error('加载画像失败:', e); }
  }

  _renderProfileItem(profile) {
    const title = this._escape(profile.position?.title || '未知岗位');
    const skills = (profile.requirements?.skills || []).slice(0, 4).map(s => s.name).filter(Boolean);
    const dimensions = (profile._signal_dimensions || []).map(s => s.category).filter(Boolean).slice(0, 3);
    const meta = dimensions.length ? dimensions.join(' / ') : skills.join(' / ');
    const sourceLabel = profile._source === 'portrait' ? '来自人才画像' : '面试画像';
    return `
      <div class="saved-item source-item" data-id="${profile._id}" onclick="window.interviewSetup.selectProfile('${profile._id}', this)">
        <div class="saved-item-header">
          <strong>${title}</strong>
          <span class="badge">${sourceLabel}</span>
        </div>
        <div class="saved-item-info">${this._escape(meta || '暂无信号维度')}</div>
        <div class="saved-item-actions">
          <button type="button" class="btn-use" onclick="event.stopPropagation(); window.interviewSetup.useProfile('${profile._id}')">选用</button>
        </div>
      </div>`;
  }

  selectProfile(id, el) {
    this.selectedProfileId = id;
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#profile-list');
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    this._updateSelectedHint(container);
  }

  useProfile(id) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#profile-list');
    const target = list.querySelector(`.saved-item[data-id="${id}"]`);
    if (target) this.selectProfile(id, target);
  }

  async _loadCandidates() {
    try {
      const data = await api.listCandidates();
      const container = document.querySelector('.interview-container');
      if (!container) return;

      const list = container.querySelector('#candidate-list');
      const count = container.querySelector('#candidate-count');
      this.candidates = data.success ? data.candidates : [];
      if (this.candidates.length) {
        count.textContent = this.candidates.length;
        list.innerHTML = this.candidates.map(c => this._renderCandidateItem(c)).join('');
        if (this.selectedCandidateId) {
          const target = list.querySelector(`[data-id="${this.selectedCandidateId}"]`);
          if (target) target.classList.add('selected');
        }
      } else {
        count.textContent = '0';
        list.innerHTML = `
          <div class="source-empty-state">
            <strong>暂无简历分析结果</strong>
            <span>请先在简历分析页上传并解析简历。</span>
          </div>
        `;
      }
      this._updateSelectedHint(container);
    } catch (e) { console.error('加载候选人失败:', e); }
  }

  _renderCandidateItem(candidate) {
    const name = this._escape(candidate.name || '未知候选人');
    const expCount = candidate.experiences?.length || 0;
    const skillCount = candidate.skills?.length || 0;
    const blindSpotCount = candidate._blind_spots?.length || 0;
    const summary = [
      `${expCount} 段经历`,
      `${skillCount} 条技能/声明`,
      blindSpotCount ? `${blindSpotCount} 个待澄清点` : '',
    ].filter(Boolean).join(' · ');
    const sourceLabel = candidate._source === 'resume_parser' ? '来自简历解析' : '候选人档案';
    return `
      <div class="saved-item source-item" data-id="${candidate._id}" onclick="window.interviewSetup.selectCandidate('${candidate._id}', this)">
        <div class="saved-item-header">
          <strong>${name}</strong>
          <span class="badge">${sourceLabel}</span>
        </div>
        <div class="saved-item-info">${this._escape(summary || candidate.summary || '暂无摘要')}</div>
        <div class="saved-item-actions">
          <button type="button" class="btn-use" onclick="event.stopPropagation(); window.interviewSetup.useCandidate('${candidate._id}')">选用</button>
        </div>
      </div>`;
  }

  selectCandidate(id, el) {
    this.selectedCandidateId = id;
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#candidate-list');
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    this._updateSelectedHint(container);
  }

  useCandidate(id) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#candidate-list');
    const target = list.querySelector(`.saved-item[data-id="${id}"]`);
    if (target) this.selectCandidate(id, target);
  }

  _updateSelectedHint(container) {
    const hint = container.querySelector('#selected-data-hint');
    const btn = container.querySelector('#btn-start');
    const profile = this.profiles.find(p => p._id === this.selectedProfileId);
    const candidate = this.candidates.find(c => c._id === this.selectedCandidateId);

    if (profile && candidate) {
      hint.className = 'selected-source-summary ready';
      hint.innerHTML = `
        <strong>已选择：</strong>
        <span>${this._escape(profile.position?.title || '人才画像')}</span>
        <span>+</span>
        <span>${this._escape(candidate.name || '简历分析结果')}</span>
        <small>AI 将结合画像信号和简历证据生成问题。</small>
      `;
      btn.disabled = false;
      return;
    }

    const missing = [];
    if (!profile) missing.push('人才画像');
    if (!candidate) missing.push('简历分析结果');
    hint.className = 'selected-source-summary';
    hint.textContent = `还需要选择${missing.join('和')}。`;
    btn.disabled = true;
  }

  async _startInterview(container) {
    const btn = container.querySelector('#btn-start');
    const profile = this.profiles.find(p => p._id === this.selectedProfileId);
    const candidate = this.candidates.find(c => c._id === this.selectedCandidateId);
    if (!profile || !candidate) {
      this._showStartError(container, { error: '请先选择人才画像和简历分析结果' });
      this._updateSelectedHint(container);
      return;
    }

    btn.disabled = true;
    btn.textContent = '⏳ 正在准备面试...';

    const body = {
      profile_id: this.selectedProfileId,
      candidate_id: this.selectedCandidateId,
      duration: parseInt(container.querySelector('#duration').value, 10) || 45,
    };

    try {
      const data = await api.startInterview(body);
      if (data.success) {
        window.location.hash = '#/interview/' + data.interview.interview_id;
      } else {
        this._showStartError(container, data);
        btn.disabled = false;
        btn.textContent = '开始 AI 面试';
      }
    } catch (err) {
      this._showStartError(container, { error: '网络错误: ' + err.message, need_llm: false });
      btn.disabled = false;
      btn.textContent = '开始 AI 面试';
    }
  }

  _showStartError(container, data) {
    let errorDiv = container.querySelector('#start-error');
    if (!errorDiv) {
      errorDiv = document.createElement('div');
      errorDiv.id = 'start-error';
      const btn = container.querySelector('.btn-start-interview');
      btn.parentNode.insertBefore(errorDiv, btn.nextSibling);
    }

    errorDiv.style.display = 'block';
    errorDiv.innerHTML = '';

    if (data.need_llm) {
      errorDiv.className = 'start-error need-llm';
      errorDiv.innerHTML = `
        <div class="error-icon">🧠</div>
        <div class="error-title">需要配置大语言模型</div>
        <div class="error-desc">${this._escape(data.error)}</div>
        <button type="button" class="btn-goto-config" onclick="document.getElementById('llm-config-body').style.display='block';document.getElementById('llm-config-body').scrollIntoView({behavior:'smooth'});">立即配置</button>
      `;
    } else {
      errorDiv.className = 'start-error';
      errorDiv.innerHTML = `
        <div class="error-icon">!</div>
        <div class="error-title">启动失败</div>
        <div class="error-desc">${this._escape(data.error || data.detail || '请检查配置后重试')}</div>
      `;
    }
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

window.interviewSetup = new InterviewSetup();
