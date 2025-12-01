document.addEventListener('DOMContentLoaded', () => {
  // attach to all add-to-playlist forms
  document.querySelectorAll('.add-to-playlist-form').forEach(form => {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const data = new FormData(form);
      try {
        const resp = await fetch(form.action, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: data
        });
        if (resp.ok) {
          const json = await resp.json().catch(() => null);
          showToast((json && json.message) || 'Added to playlist', 'success');
        } else {
          const txt = await resp.text();
          showToast('Failed to add', 'error');
          console.error('Add failed', resp.status, txt);
        }
      } catch (err) {
        console.error(err);
        showToast('Network error', 'error');
      }
    });
  });

  // Toast helper
  function showToast(msg, type='info'){
    const container = document.getElementById('toast-container');
    if(!container) return;
    const el = document.createElement('div');
    el.className = 'toast-item ' + type;
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(()=>{ el.classList.add('visible'); }, 10);
    setTimeout(()=>{ el.classList.remove('visible'); setTimeout(()=>el.remove(),300); }, 3800);
  }

  // Simple searchable select enhancement for settings favorites
  const filterInputs = document.querySelectorAll('.select-filter');
  if (filterInputs.length) {
    filterInputs.forEach(inp => {
      const targetId = inp.getAttribute('data-target');
      const sel = document.getElementById(targetId);
      if (!sel) return;

      // debounce helper
      let timer = null;
      inp.addEventListener('input', (e) => {
        clearTimeout(timer);
        const qraw = e.target.value || '';
        const q = qraw.toLowerCase().trim();
        timer = setTimeout(async () => {
          // Iterate existing options and hide those that don't match
          let anyVisible = false;
          for (let i = 0; i < sel.options.length; i++) {
            const opt = sel.options[i];
            if (!opt.value) { opt.hidden = false; continue; }
            const txt = (opt.text || '').toLowerCase();
            if (!q || txt.includes(q)) {
              opt.hidden = false; anyVisible = true;
            } else {
              opt.hidden = true;
            }
          }

          // If nothing visible and query long enough, try server search
          if ((!anyVisible || (q && !anyVisible)) && q.length >= 2) {
            try {
              const resp = await fetch(`/api/search-tracks?q=${encodeURIComponent(q)}&limit=50`);
              if (resp.ok) {
                const list = await resp.json();
                // rebuild options from server results
                sel.innerHTML = '';
                const empty = document.createElement('option'); empty.value=''; empty.text='(no selection)'; sel.appendChild(empty);
                list.forEach(item => {
                  const o = document.createElement('option');
                  o.value = item.row_id; o.text = item.label; sel.appendChild(o);
                });
                // nothing selected by default
                sel.value = '';
                anyVisible = sel.options.length > 1;
              }
            } catch (err) {
              console.error('Search error', err);
            }
          }

          // If the currently selected option was hidden by the filter, reset selection to empty
          const selected = sel.options[sel.selectedIndex];
          if (selected && selected.hidden) {
            sel.value = '';
          }
        }, 280);
      });
    });
  }

});
