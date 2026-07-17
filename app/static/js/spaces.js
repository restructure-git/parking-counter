/* 駐車枠管理画面: 画像上でドラッグして矩形（駐車枠）を登録する。
 *
 * 座標は「バックエンドが判定時に使うリサイズ後の座標系
 * （幅 = IMAGE_MAX_WIDTH 以下）」で保存する。キャンバス表示はさらに
 * 見た目用に縮小しているだけなので、保存時に displayScale で逆算する。
 */
(function () {
  const DISPLAY_MAX_WIDTH = 800;

  const canvas = document.getElementById('space-canvas');
  const ctx = canvas.getContext('2d');
  const fileInput = document.getElementById('canvas-image-input');
  const statusMsg = document.getElementById('canvas-status');

  const STATUS_COLOR = '#1a73e8';

  let bgImage = null;
  let naturalWidth = 0;
  let naturalHeight = 0;
  let effectiveWidth = 0;
  let displayScale = 1;
  let dragStart = null;
  let dragCurrent = null;

  function getPos(evt) {
    const rect = canvas.getBoundingClientRect();
    const point = evt.touches ? evt.touches[0] : evt;
    return {
      x: point.clientX - rect.left,
      y: point.clientY - rect.top,
    };
  }

  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (bgImage) {
      ctx.drawImage(bgImage, 0, 0, canvas.width, canvas.height);
    }
    window.EXISTING_SPACES.forEach((s) => {
      drawEffectiveRect(s.x, s.y, s.width, s.height, STATUS_COLOR, s.name);
    });
    if (dragStart && dragCurrent) {
      const x = Math.min(dragStart.x, dragCurrent.x);
      const y = Math.min(dragStart.y, dragCurrent.y);
      const w = Math.abs(dragCurrent.x - dragStart.x);
      const h = Math.abs(dragCurrent.y - dragStart.y);
      ctx.strokeStyle = '#d93025';
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);
    }
  }

  function drawEffectiveRect(effX, effY, effW, effH, color, label) {
    const x = effX * displayScale;
    const y = effY * displayScale;
    const w = effW * displayScale;
    const h = effH * displayScale;
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
    if (label) {
      ctx.fillStyle = color;
      ctx.font = '12px sans-serif';
      ctx.fillText(label, x + 2, y + 12);
    }
  }

  fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;
    const img = new Image();
    img.onload = () => {
      bgImage = img;
      naturalWidth = img.naturalWidth;
      naturalHeight = img.naturalHeight;
      effectiveWidth = Math.min(naturalWidth, window.IMAGE_MAX_WIDTH);
      const effScale = effectiveWidth / naturalWidth;
      const effectiveHeight = Math.round(naturalHeight * effScale);

      const displayWidth = Math.min(DISPLAY_MAX_WIDTH, effectiveWidth);
      displayScale = displayWidth / effectiveWidth;
      const displayHeight = Math.round(effectiveHeight * displayScale);

      canvas.width = displayWidth;
      canvas.height = displayHeight;
      statusMsg.textContent = '画像上をドラッグして駐車枠を描いてください。';
      redraw();
    };
    img.onerror = () => {
      statusMsg.textContent = '画像を読み込めませんでした。';
    };
    img.src = URL.createObjectURL(file);
  });

  function onDragStart(evt) {
    if (!bgImage) return;
    evt.preventDefault();
    dragStart = getPos(evt);
    dragCurrent = dragStart;
  }

  function onDragMove(evt) {
    if (!dragStart) return;
    evt.preventDefault();
    dragCurrent = getPos(evt);
    redraw();
  }

  async function onDragEnd(evt) {
    if (!dragStart) return;
    evt.preventDefault();
    const end = getPos(evt);
    const x1 = Math.min(dragStart.x, end.x);
    const y1 = Math.min(dragStart.y, end.y);
    const w = Math.abs(end.x - dragStart.x);
    const h = Math.abs(end.y - dragStart.y);
    dragStart = null;
    dragCurrent = null;
    redraw();

    if (w < 8 || h < 8) {
      return; // 小さすぎるドラッグは無視
    }

    const name = window.prompt('この駐車枠の名前を入力してください（例: A-01）');
    if (!name) {
      return;
    }

    const effX = Math.round(x1 / displayScale);
    const effY = Math.round(y1 / displayScale);
    const effW = Math.round(w / displayScale);
    const effH = Math.round(h / displayScale);

    try {
      const response = await fetch('/admin/spaces/api', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, x: effX, y: effY, width: effW, height: effH }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || '登録に失敗しました。');
      }
      statusMsg.textContent = `駐車枠「${data.name}」を登録しました。ページを再読み込みします。`;
      window.setTimeout(() => window.location.reload(), 600);
    } catch (err) {
      statusMsg.textContent = err.message || '登録に失敗しました。';
    }
  }

  canvas.addEventListener('mousedown', onDragStart);
  canvas.addEventListener('mousemove', onDragMove);
  window.addEventListener('mouseup', onDragEnd);
  canvas.addEventListener('touchstart', onDragStart, { passive: false });
  canvas.addEventListener('touchmove', onDragMove, { passive: false });
  canvas.addEventListener('touchend', onDragEnd, { passive: false });

  window.addEventListener('DOMContentLoaded', redraw);
})();
