(() => {
  'use strict';
  const data = JSON.parse(document.getElementById('report-evidence-data').textContent);
  const ordered = Object.keys(data);
  const dialog = document.getElementById('lightbox');
  const stage = document.getElementById('lightbox-stage');
  const zoom = document.getElementById('zoom-image');
  let activeId = null;
  let lastFocus = null;
  const $ = id => document.getElementById(id);

  function showImage(id) {
    const item = data[id];
    if (!item) return;
    activeId = id;
    $('lightbox-title').textContent = item.title;
    $('lightbox-kicker').textContent = id + ' · ' + item.date;
    $('lightbox-image').src = item.url;
    $('lightbox-image').alt = id + ' ' + item.title;
    $('original-image').href = item.url;
    $('lightbox-caption').textContent = item.caption;
    const details = $('lightbox-details');
    details.replaceChildren();
    for (const [label, text] of [['操作步骤', item.steps], ['结论边界', item.finding], ['证据状态', item.state]]) {
      const div = document.createElement('div');
      div.textContent = label + '：' + text;
      details.append(div);
    }
    const path = document.createElement('code');
    path.textContent = '原始文件：' + item.path;
    details.append(path);
    stage.classList.remove('actual');
    stage.scrollTop = stage.scrollLeft = 0;
    zoom.textContent = '原始尺寸';
    zoom.setAttribute('aria-pressed', 'false');
    $('lightbox-position').textContent = (ordered.indexOf(id) + 1) + ' / ' + ordered.length + ' · 含2张环境附图';
    $('previous-image').disabled = ordered.indexOf(id) === 0;
    $('next-image').disabled = ordered.indexOf(id) === ordered.length - 1;
    if (!dialog.open) {
      lastFocus = document.activeElement;
      dialog.showModal();
      document.body.classList.add('modal-open');
      $('close-lightbox').focus();
    }
  }
  function changeImage(delta) {
    const next = ordered[ordered.indexOf(activeId) + delta];
    if (next) showImage(next);
  }
  function closeImage() { if (dialog.open) dialog.close(); }
  document.addEventListener('click', event => {
    const direct = event.target.closest('[data-image]');
    const ref = event.target.closest('[data-evidence]');
    if (direct) showImage(direct.dataset.image);
    else if (ref) {
      const id = ref.dataset.evidence;
      showImage(data[id] ? id : id + '-V');
    }
  });
  $('close-lightbox').addEventListener('click', closeImage);
  dialog.addEventListener('click', event => { if (event.target === dialog) closeImage(); });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('modal-open');
    if (lastFocus && lastFocus.isConnected) lastFocus.focus({preventScroll:true});
  });
  $('previous-image').addEventListener('click', () => changeImage(-1));
  $('next-image').addEventListener('click', () => changeImage(1));
  document.addEventListener('keydown', event => {
    if (!dialog.open) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); changeImage(-1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); changeImage(1); }
  });
  zoom.addEventListener('click', () => {
    const isActual = stage.classList.toggle('actual');
    zoom.textContent = isActual ? '适应窗口' : '原始尺寸';
    zoom.setAttribute('aria-pressed', String(isActual));
  });

  const rows = [...document.querySelectorAll('#evidence-table tbody tr')];
  const filter = () => {
    const query = $('evidence-search').value.trim().toLocaleLowerCase();
    const section = $('evidence-filter').value;
    let visible = 0;
    for (const row of rows) {
      const matches = row.textContent.toLocaleLowerCase().includes(query) && (!section || row.cells[2].textContent === section);
      row.hidden = !matches;
      if (matches) visible++;
    }
    $('evidence-count').textContent = visible + ' / ' + rows.length + ' 张';
  };
  $('evidence-search').addEventListener('input', filter);
  $('evidence-filter').addEventListener('change', filter);

  const menu = document.querySelector('.mobile-nav');
  menu.addEventListener('click', () => {
    const open = document.body.classList.toggle('nav-open');
    menu.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('nav a').forEach(link => link.addEventListener('click', () => {
    document.body.classList.remove('nav-open');
    menu.setAttribute('aria-expanded', 'false');
  }));
  const sections = [...document.querySelectorAll('.report-section')];
  const navLinks = [...document.querySelectorAll('[data-nav]')];
  let scheduled = false;
  function updateActive() {
    scheduled = false;
    let current = sections[0].id;
    const offset = innerWidth <= 650 ? 100 : 90;
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= offset) current = section.id;
    }
    navLinks.forEach(link => {
      const active = link.dataset.nav === current;
      link.classList.toggle('active', active);
      if (active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; requestAnimationFrame(updateActive); }
  }, {passive:true});
  updateActive();
  $('print-report').addEventListener('click', () => window.print());
  document.querySelectorAll('a[href^="#img-"]').forEach(link => link.addEventListener('click', () => {
    const target = document.getElementById(link.hash.slice(1));
    if (!target) return;
    let parent = target.parentElement;
    while (parent) {
      if (parent.tagName === 'DETAILS') parent.open = true;
      parent = parent.parentElement;
    }
    target.classList.add('highlight');
    setTimeout(() => target.classList.remove('highlight'), 2000);
  }));
})();
