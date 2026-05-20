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
  }

  init(container) {
    container.innerHTML = `
      <div class="interview-container">
        <div class="interview-hero">
          <h1>AI 驱动的智能面试系统</h1>
          <p>基于人才画像与候选人档案，自动生成面试方案，支持语音交互与实时追问</p>
        </div>

        <div class="setup-card">
          <h2>开始一场新的面试</h2>
          <p class="card-desc">配置面试参数，AI 将自动生成面试方案</p>

          <form id="interview-form">
            <div class="form-section">
              <h3><span class="section-icon">📋</span> 岗位信息</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>岗位名称</label>
                  <input type="text" id="position-title" value="高级后端开发工程师" placeholder="例如：高级前端工程师">
                </div>
                <div class="form-group">
                  <label>职级</label>
                  <select id="position-level">
                    <option value="初级">初级</option>
                    <option value="中级">中级</option>
                    <option value="高级" selected>高级</option>
                    <option value="专家">专家</option>
                    <option value="架构师">架构师</option>
                  </select>
                </div>
              </div>
            </div>

            <div class="form-section">
              <h3><span class="section-icon">🔧</span> 技能要求</h3>
              <div id="skills-container">
                <div class="skill-row">
                  <input type="text" class="skill-name" value="Python" placeholder="技能名称">
                  <select class="skill-level">
                    <option value="了解">了解</option>
                    <option value="熟悉">熟悉</option>
                    <option value="精通" selected>精通</option>
                  </select>
                  <button type="button" class="btn-remove-skill" onclick="this.parentElement.remove()">✕</button>
                </div>
                <div class="skill-row">
                  <input type="text" class="skill-name" value="Flask" placeholder="技能名称">
                  <select class="skill-level">
                    <option value="了解">了解</option>
                    <option value="熟悉">熟悉</option>
                    <option value="精通" selected>精通</option>
                  </select>
                  <button type="button" class="btn-remove-skill" onclick="this.parentElement.remove()">✕</button>
                </div>
                <div class="skill-row">
                  <input type="text" class="skill-name" value="MySQL" placeholder="技能名称">
                  <select class="skill-level">
                    <option value="了解">了解</option>
                    <option value="熟悉" selected>熟悉</option>
                    <option value="精通">精通</option>
                  </select>
                  <button type="button" class="btn-remove-skill" onclick="this.parentElement.remove()">✕</button>
                </div>
              </div>
              <button type="button" class="btn-add-skill" id="btn-add-skill">+ 添加技能</button>
            </div>

            <div class="form-section">
              <h3><span class="section-icon">⚙️</span> 面试设置</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>面试时长（分钟）</label>
                  <input type="number" id="duration" value="45" min="15" max="120">
                </div>
                <div class="form-group">
                  <label style="display:flex;align-items:center;gap:8px;">
                    <input type="checkbox" id="enable-voice" checked style="width:18px;height:18px;accent-color:var(--color-primary);">
                    启用语音交互
                  </label>
                </div>
              </div>
            </div>

            <button type="submit" class="btn-start-interview" id="btn-start">
              🎙️ 开始 AI 面试
            </button>

            <div id="selected-data-hint" class="selected-hint" style="display:none;"></div>
          </form>
        </div>

        <!-- 人才画像管理 -->
        <div class="collapse-panel">
          <div class="collapse-header" id="profile-collapse-header">
            <h3><span class="section-icon">📋</span> 人才画像管理 <span class="badge-count" id="profile-count">0</span></h3>
            <span style="color:var(--color-text-secondary);font-size:13px;">对接画像模块</span>
          </div>
          <div class="collapse-body" id="profile-panel-body" style="display:none;">
            <p class="collapse-desc">已保存的人才画像可在开始面试时直接选用</p>
            <div class="saved-list" id="profile-list"><div class="empty-hint">暂无已保存的画像</div></div>
            <div class="panel-actions">
              <button type="button" class="btn-save-config" id="btn-show-profile-form">➕ 新建画像</button>
              <button type="button" class="btn-test" id="btn-refresh-profiles">🔄 刷新</button>
            </div>
            <div id="profile-form" class="inline-form" style="display:none;">
              <div class="form-section">
                <div class="form-row">
                  <div class="form-group"><label>岗位名称</label><input type="text" id="pf-title" value="高级后端开发工程师"></div>
                  <div class="form-group"><label>职级</label><select id="pf-level"><option>初级</option><option>中级</option><option selected>高级</option><option>专家</option><option>架构师</option></select></div>
                </div>
                <div class="form-row">
                  <div class="form-group"><label>部门</label><input type="text" id="pf-dept" value="技术部"></div>
                  <div class="form-group"><label>薪资范围</label><input type="text" id="pf-salary" value="25K-40K"></div>
                </div>
              </div>
              <div class="form-section">
                <label style="display:block;font-size:13px;font-weight:600;color:var(--color-text-secondary);margin-bottom:6px;">技能要求（每行一个：名称, 精通/熟悉/了解）</label>
                <textarea id="pf-skills" rows="4" class="form-textarea">Python, 精通\nFlask, 精通\nMySQL, 熟悉</textarea>
              </div>
              <div class="form-section">
                <label style="display:block;font-size:13px;font-weight:600;color:var(--color-text-secondary);margin-bottom:6px;">软技能（逗号分隔）</label>
                <input type="text" id="pf-soft-skills" value="团队协作, 沟通表达, 问题解决" class="form-input">
              </div>
              <div class="llm-actions">
                <button type="button" class="btn-save-config" id="btn-save-profile">💾 保存画像</button>
                <button type="button" class="btn-test" id="btn-hide-profile-form">取消</button>
              </div>
              <div id="profile-form-result" class="llm-test-result"></div>
            </div>
          </div>
        </div>

        <!-- 候选人管理 -->
        <div class="collapse-panel">
          <div class="collapse-header" id="candidate-collapse-header">
            <h3><span class="section-icon">👤</span> 候选人档案管理 <span class="badge-count" id="candidate-count">0</span></h3>
            <span style="color:var(--color-text-secondary);font-size:13px;">对接简历模块</span>
          </div>
          <div class="collapse-body" id="candidate-panel-body" style="display:none;">
            <p class="collapse-desc">已保存的候选人档案可在开始面试时作为面试背景</p>
            <div class="saved-list" id="candidate-list"><div class="empty-hint">暂无已保存的候选人</div></div>
            <div class="panel-actions">
              <button type="button" class="btn-save-config" id="btn-show-candidate-form">➕ 新建候选人</button>
              <button type="button" class="btn-test" id="btn-refresh-candidates">🔄 刷新</button>
            </div>
            <div id="candidate-form" class="inline-form" style="display:none;">
              <div class="form-section">
                <div class="form-row">
                  <div class="form-group"><label>姓名</label><input type="text" id="ca-name" value="张三"></div>
                  <div class="form-group"><label>概述</label><input type="text" id="ca-summary" value="5年后端开发经验"></div>
                </div>
              </div>
              <div class="form-section">
                <label style="display:block;font-size:13px;font-weight:600;color:var(--color-text-secondary);margin-bottom:6px;">工作经历（每行一个：公司, 职位, 描述）</label>
                <textarea id="ca-experiences" rows="3" class="form-textarea">某科技公司, 高级开发, 负责核心业务后端开发与架构设计</textarea>
              </div>
              <div class="form-section">
                <label style="display:block;font-size:13px;font-weight:600;color:var(--color-text-secondary);margin-bottom:6px;">已有技能（每行一个：名称, 水平）</label>
                <textarea id="ca-skills" rows="2" class="form-textarea">Python, 精通\nJava, 熟悉</textarea>
              </div>
              <div class="llm-actions">
                <button type="button" class="btn-save-config" id="btn-save-candidate">💾 保存候选人</button>
                <button type="button" class="btn-test" id="btn-hide-candidate-form">取消</button>
              </div>
              <div id="candidate-form-result" class="llm-test-result"></div>
            </div>
          </div>
        </div>

        <!-- LLM 配置 -->
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

    return () => {
      // Cleanup portrait nav buttons when leaving
      document.querySelectorAll('.portrait-nav-btn').forEach(b => b.remove());
    };
  }

  _bindEvents(container) {
    // Collapsible panels
    container.querySelector('#profile-collapse-header').addEventListener('click', () => {
      const body = container.querySelector('#profile-panel-body');
      body.style.display = body.style.display === 'none' ? 'block' : 'none';
    });

    container.querySelector('#candidate-collapse-header').addEventListener('click', () => {
      const body = container.querySelector('#candidate-panel-body');
      body.style.display = body.style.display === 'none' ? 'block' : 'none';
    });

    container.querySelector('#llm-collapse-header').addEventListener('click', () => {
      const body = container.querySelector('#llm-config-body');
      body.style.display = body.style.display === 'none' ? 'block' : 'none';
    });

    // Add skill
    container.querySelector('#btn-add-skill').addEventListener('click', () => {
      const skillsContainer = container.querySelector('#skills-container');
      const row = document.createElement('div');
      row.className = 'skill-row';
      row.innerHTML = `
        <input type="text" class="skill-name" placeholder="技能名称">
        <select class="skill-level">
          <option value="了解">了解</option>
          <option value="熟悉" selected>熟悉</option>
          <option value="精通">精通</option>
        </select>
        <button type="button" class="btn-remove-skill" onclick="this.parentElement.remove()">✕</button>
      `;
      skillsContainer.appendChild(row);
    });

    // Profile form
    container.querySelector('#btn-show-profile-form').addEventListener('click', () => {
      container.querySelector('#profile-form').style.display = 'block';
    });
    container.querySelector('#btn-hide-profile-form').addEventListener('click', () => {
      container.querySelector('#profile-form').style.display = 'none';
    });
    container.querySelector('#btn-save-profile').addEventListener('click', () => this._saveProfile(container));
    container.querySelector('#btn-refresh-profiles').addEventListener('click', () => this._loadProfiles());

    // Candidate form
    container.querySelector('#btn-show-candidate-form').addEventListener('click', () => {
      container.querySelector('#candidate-form').style.display = 'block';
    });
    container.querySelector('#btn-hide-candidate-form').addEventListener('click', () => {
      container.querySelector('#candidate-form').style.display = 'none';
    });
    container.querySelector('#btn-save-candidate').addEventListener('click', () => this._saveCandidate(container));
    container.querySelector('#btn-refresh-candidates').addEventListener('click', () => this._loadCandidates());

    // LLM config
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

    // Form submit
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
      if (data.success && data.profiles.length) {
        count.textContent = data.profiles.length;
        list.innerHTML = data.profiles.map(p => {
          const title = p.position?.title || '未知岗位';
          const level = p.position?.level || '';
          const skills = (p.requirements?.skills || []).map(s => s.name).join(', ');
          return `
            <div class="saved-item" data-id="${p._id}" onclick="window.interviewSetup.selectProfile('${p._id}', this)">
              <div class="saved-item-header"><strong>${title}</strong> ${level ? '<span class="badge">' + level + '</span>' : ''}</div>
              <div class="saved-item-info">${skills || '无技能'}</div>
              <div class="saved-item-actions">
                <button class="btn-use" onclick="event.stopPropagation(); window.interviewSetup.useProfile('${p._id}')">🎯 选用</button>
                <button class="btn-del" onclick="event.stopPropagation(); window.interviewSetup.deleteProfile('${p._id}')">🗑</button>
              </div>
            </div>`;
        }).join('');
      } else {
        count.textContent = '0';
        list.innerHTML = '<div class="empty-hint">暂无已保存的画像</div>';
      }
    } catch (e) { console.error('加载画像失败:', e); }
  }

  selectProfile(id, el) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#profile-list');
    list.dataset.selectedId = id;
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    this._updateSelectedHint(container);
  }

  async useProfile(id) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#profile-list');
    list.dataset.selectedId = id;
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    const target = list.querySelector(`.saved-item[data-id="${id}"]`);
    if (target) target.classList.add('selected');
    this._updateSelectedHint(container);
  }

  async deleteProfile(id) {
    if (!confirm('确定删除此画像？')) return;
    try {
      await api.deleteInterviewProfile(id);
      this._loadProfiles();
    } catch (e) { showToast(e.message, 'error'); }
  }

  async _loadCandidates() {
    try {
      const data = await api.listCandidates();
      const container = document.querySelector('.interview-container');
      if (!container) return;

      const list = container.querySelector('#candidate-list');
      const count = container.querySelector('#candidate-count');
      if (data.success && data.candidates.length) {
        count.textContent = data.candidates.length;
        list.innerHTML = data.candidates.map(c => {
          return `
            <div class="saved-item" data-id="${c._id}" onclick="window.interviewSetup.selectCandidate('${c._id}', this)">
              <div class="saved-item-header"><strong>${this._escape(c.name || '未知')}</strong></div>
              <div class="saved-item-info">${this._escape(c.summary || '')}</div>
              <div class="saved-item-actions">
                <button class="btn-use" onclick="event.stopPropagation(); window.interviewSetup.useCandidate('${c._id}')">🎯 选用</button>
                <button class="btn-del" onclick="event.stopPropagation(); window.interviewSetup.deleteCandidate('${c._id}')">🗑</button>
              </div>
            </div>`;
        }).join('');
      } else {
        count.textContent = '0';
        list.innerHTML = '<div class="empty-hint">暂无已保存的候选人</div>';
      }
    } catch (e) { console.error('加载候选人失败:', e); }
  }

  selectCandidate(id, el) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#candidate-list');
    list.dataset.selectedId = id;
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    el.classList.add('selected');
    this._updateSelectedHint(container);
  }

  async useCandidate(id) {
    const container = document.querySelector('.interview-container');
    const list = container.querySelector('#candidate-list');
    list.dataset.selectedId = id;
    list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    const target = list.querySelector(`.saved-item[data-id="${id}"]`);
    if (target) target.classList.add('selected');
    this._updateSelectedHint(container);
  }

  async deleteCandidate(id) {
    if (!confirm('确定删除此候选人？')) return;
    try {
      await api.deleteCandidate(id);
      this._loadCandidates();
    } catch (e) { showToast(e.message, 'error'); }
  }

  _updateSelectedHint(container) {
    const pList = container.querySelector('#profile-list');
    const cList = container.querySelector('#candidate-list');
    const hint = container.querySelector('#selected-data-hint');
    const pid = pList?.dataset?.selectedId;
    const cid = cList?.dataset?.selectedId;
    if (pid || cid) {
      let text = '';
      if (pid) text += '📋 画像已选 | ';
      if (cid) text += '👤 简历已选 | ';
      text += '点击「开始 AI 面试」使用';
      hint.style.display = 'block';
      hint.innerHTML = `✅ ${text} <button onclick="window.interviewSetup.clearSelections()" style="background:none;border:none;color:var(--color-destructive);cursor:pointer;font-size:13px;float:right;">✕ 清除</button>`;
    } else {
      hint.style.display = 'none';
    }
  }

  clearSelections() {
    const container = document.querySelector('.interview-container');
    ['profile-list', 'candidate-list'].forEach(id => {
      const list = container.querySelector('#' + id);
      delete list.dataset.selectedId;
      list.querySelectorAll('.saved-item').forEach(i => i.classList.remove('selected'));
    });
    this._updateSelectedHint(container);
  }

  async _saveProfile(container) {
    const btn = container.querySelector('#btn-save-profile');
    const result = container.querySelector('#profile-form-result');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';

    const skills = container.querySelector('#pf-skills').value.trim().split('\n')
      .filter(s => s.trim())
      .map(s => {
        const parts = s.split(',').map(x => x.trim());
        return { name: parts[0], level: parts[1] || '熟悉', weight: parts[1] === '精通' ? 9 : 6 };
      });
    const softSkills = container.querySelector('#pf-soft-skills').value.split(',').map(s => s.trim()).filter(s => s);

    const profile = {
      position: {
        title: container.querySelector('#pf-title').value,
        department: container.querySelector('#pf-dept').value,
        level: container.querySelector('#pf-level').value,
        salary_range: container.querySelector('#pf-salary').value,
      },
      requirements: {
        education: { min_degree: '本科', preferred_majors: [] },
        experience: { min_years: 3, preferred_industries: [] },
        skills: skills,
        soft_skills: softSkills,
      },
      qualifications: { certifications: [], projects: [], other: [] },
      culture_fit: { team_size: '', work_style: '', values: [] }
    };

    try {
      const data = await api.createInterviewProfile(profile);
      if (data.success) {
        result.className = 'llm-test-result success';
        result.textContent = '✅ 画像已保存';
        this._loadProfiles();
      } else {
        result.className = 'llm-test-result error';
        result.textContent = '❌ ' + (data.error || '保存失败');
      }
    } catch (e) {
      result.className = 'llm-test-result error';
      result.textContent = '❌ ' + e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = '💾 保存画像';
    }
  }

  async _saveCandidate(container) {
    const btn = container.querySelector('#btn-save-candidate');
    const result = container.querySelector('#candidate-form-result');
    btn.disabled = true;
    btn.textContent = '⏳ 保存中...';

    const experiences = container.querySelector('#ca-experiences').value.trim().split('\n')
      .filter(s => s.trim())
      .map(s => {
        const parts = s.split(',').map(x => x.trim());
        return { company: parts[0] || '', title: parts[1] || '', description: parts[2] || '' };
      });
    const skills = container.querySelector('#ca-skills').value.trim().split('\n')
      .filter(s => s.trim())
      .map(s => {
        const parts = s.split(',').map(x => x.trim());
        return { name: parts[0], level: parts[1] || '熟悉' };
      });

    const candidate = {
      name: container.querySelector('#ca-name').value,
      summary: container.querySelector('#ca-summary').value,
      experiences: experiences,
      skills: skills,
      education: [],
      contact: {},
      external_profiles: {}
    };

    try {
      const data = await api.createCandidate(candidate);
      if (data.success) {
        result.className = 'llm-test-result success';
        result.textContent = '✅ 候选人已保存';
        this._loadCandidates();
      } else {
        result.className = 'llm-test-result error';
        result.textContent = '❌ ' + (data.error || '保存失败');
      }
    } catch (e) {
      result.className = 'llm-test-result error';
      result.textContent = '❌ ' + e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = '💾 保存候选人';
    }
  }

  async _startInterview(container) {
    const btn = container.querySelector('#btn-start');
    btn.disabled = true;
    btn.textContent = '⏳ 正在准备面试...';

    const skills = [];
    container.querySelectorAll('.skill-row').forEach(row => {
      const name = row.querySelector('.skill-name').value.trim();
      const level = row.querySelector('.skill-level').value;
      if (name) skills.push({ name, level, weight: level === '精通' ? 9 : level === '熟悉' ? 6 : 3 });
    });

    const profile = {
      position: {
        title: container.querySelector('#position-title').value,
        department: '技术部',
        level: container.querySelector('#position-level').value,
        salary_range: '面议'
      },
      requirements: {
        education: { min_degree: '本科', preferred_majors: ['计算机科学', '软件工程'] },
        experience: { min_years: 3, preferred_industries: ['互联网'] },
        skills: skills,
        soft_skills: ['团队协作', '沟通表达', '问题解决']
      },
      qualifications: { certifications: [], projects: [], other: [] },
      culture_fit: { team_size: '5-10人', work_style: '敏捷开发', values: ['技术驱动', '结果导向'] }
    };

    const pList = container.querySelector('#profile-list');
    const cList = container.querySelector('#candidate-list');
    const selectedProfileId = pList?.dataset?.selectedId;
    const selectedCandidateId = cList?.dataset?.selectedId;

    const body = { duration: parseInt(container.querySelector('#duration').value) };
    if (selectedProfileId) body.profile_id = selectedProfileId;
    else body.profile = profile;
    if (selectedCandidateId) body.candidate_id = selectedCandidateId;

    try {
      const data = await api.startInterview(body);
      if (data.success) {
        const voiceEnabled = container.querySelector('#enable-voice').checked;
        window.location.hash = '#/interview/' + data.interview.interview_id;
      } else {
        this._showStartError(container, data);
        btn.disabled = false;
        btn.innerHTML = '🎙️ 开始 AI 面试';
      }
    } catch (err) {
      this._showStartError(container, { error: '网络错误: ' + err.message, need_llm: false });
      btn.disabled = false;
      btn.innerHTML = '🎙️ 开始 AI 面试';
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
        <div class="error-desc">${data.error}</div>
        <button class="btn-goto-config" onclick="document.getElementById('llm-config-body').style.display='block';document.getElementById('llm-config-body').scrollIntoView({behavior:'smooth'});">⚙️ 立即配置</button>
      `;
    } else {
      errorDiv.className = 'start-error';
      errorDiv.innerHTML = `
        <div class="error-icon">❌</div>
        <div class="error-title">启动失败</div>
        <div class="error-desc">${data.error}</div>
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
