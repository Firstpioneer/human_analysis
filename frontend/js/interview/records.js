/**
 * Interview Records 模块 — 面试记录列表
 */

class InterviewRecords {
  init(container) {
    container.innerHTML = `
      <div class="records-container">
        <div class="records-header">
          <h1>📋 面试记录</h1>
          <p>查看历史面试记录与评估结果</p>
        </div>
        <div class="records-list" id="records-list">
          <div class="empty-hint">加载中...</div>
        </div>
      </div>
    `;

    this._loadRecords(container);

    return () => {};
  }

  async _loadRecords(container) {
    const listEl = container.querySelector('#records-list');
    try {
      const data = await api.listInterviews();
      if (!data.success || !data.interviews || data.interviews.length === 0) {
        listEl.innerHTML = `
          <div class="empty-state">
            <div class="empty-icon">📭</div>
            <h3>暂无面试记录</h3>
            <p>完成一次 AI 面试后，记录将在此显示</p>
            <a href="#/interview" class="btn-back">🏠 返回首页开始面试</a>
          </div>
        `;
        return;
      }

      listEl.innerHTML = data.interviews.map(interview => {
        const title = interview.candidate?.profile_ref || interview._profile?.position?.title || 'AI 面试';
        const name = interview.candidate?.name || '匿名';
        const startTime = interview.start_time ? interview.start_time.slice(0, 19).replace('T', ' ') : '--';
        const recommendation = interview.evaluation?.recommendation;
        const qualityHealth = interview.evaluation?.quality_validation?.summary?.evidence_chain_health;
        const suitability = interview.evaluation?.suitability;
        const canRestart = interview.status === '已完成' && interview._profile;

        return `
          <div class="record-card" data-id="${interview.interview_id}">
            <div class="record-header" onclick="window.location.hash='#/interview/${interview.interview_id}'">
              <h3>${this._escape(title)}</h3>
              <span class="record-status status-${interview.status}">${interview.status}</span>
            </div>
            <div class="record-body" onclick="window.location.hash='#/interview/${interview.interview_id}'">
              <div class="record-info">
                <span>🆔 ${interview.interview_id}</span>
                <span>👤 ${this._escape(name)}</span>
                <span>📅 ${startTime}</span>
              </div>
              ${suitability ? `
                <div class="record-score">
                  <span class="score-value" style="color:${suitability === '适合' ? '#10b981' : '#ef4444'}">${suitability}</span>
                  <span class="score-label">${qualityHealth ? '证据链:' + this._escape(qualityHealth) : '评估结论'}</span>
                </div>
              ` : recommendation ? `
                <div class="record-score">
                  <span class="score-value">${this._escape(recommendation)}</span>
                  <span class="score-label">${qualityHealth ? '证据链:' + this._escape(qualityHealth) : '综合结论'}</span>
                </div>
              ` : ''}
            </div>
            <div class="record-footer">
              <span class="record-detail" onclick="window.location.hash='#/interview/${interview.interview_id}'">查看详情 →</span>
              <div class="record-footer-actions">
                ${canRestart ? `<button class="btn-restart-record" onclick="event.stopPropagation(); window.interviewRecords.restartInterview('${interview.interview_id}', this)">🔄 重新开始</button>` : ''}
                <button class="btn-delete-record" onclick="event.stopPropagation(); window.interviewRecords.deleteInterview('${interview.interview_id}', this)" title="删除此记录">🗑️ 删除</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      listEl.innerHTML = `<div class="empty-state"><div class="empty-icon">❌</div><h3>加载失败</h3><p>${err.message}</p></div>`;
    }
  }

  async restartInterview(interviewId, btn) {
    btn.disabled = true;
    btn.textContent = '⏳ 重新创建中...';
    try {
      const data = await api.restartInterview(interviewId);
      if (data.success) {
        window.location.hash = '#/interview/' + data.interview.interview_id;
      } else if (data.need_llm) {
        alert('需要先配置大语言模型：' + data.error);
        window.location.hash = '#/interview';
      } else {
        alert('重新开始失败: ' + (data.error || '未知错误'));
        btn.disabled = false;
        btn.textContent = '🔄 重新开始';
      }
    } catch (e) {
      alert('网络错误: ' + e.message);
      btn.disabled = false;
      btn.textContent = '🔄 重新开始';
    }
  }

  async deleteInterview(interviewId, btn) {
    if (!confirm('确定要删除这条面试记录吗？此操作不可恢复。')) return;
    btn.disabled = true;
    btn.textContent = '⏳ 删除中...';
    try {
      const data = await api.deleteInterview(interviewId);
      if (data.success) {
        const card = btn.closest('.record-card');
        if (card) {
          card.style.transition = 'opacity 0.3s, transform 0.3s';
          card.style.opacity = '0';
          card.style.transform = 'translateX(20px)';
          setTimeout(() => card.remove(), 300);
        }
      } else {
        alert('删除失败: ' + (data.error || '未知错误'));
        btn.disabled = false;
        btn.textContent = '🗑️ 删除';
      }
    } catch (e) {
      alert('网络错误: ' + e.message);
      btn.disabled = false;
      btn.textContent = '🗑️ 删除';
    }
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

window.interviewRecords = new InterviewRecords();
