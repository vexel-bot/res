// Fixed, registered runtime shared by draft preview and frame export.
(function () {
  'use strict';
  var spec = JSON.parse(document.getElementById('res-editorial-spec').textContent);
  window.__resEditorialChecks = { ready: false, textOverflow: [], textMeasurements: [], errors: [] };
  window.__resEditorialApply = function (seconds) {
    spec.forEach(function (item) {
      var el = document.getElementById(item.id);
      if (!el) return;
      var frame = seconds * item.timing.fps;
      var local = frame - item.timing.startFrame;
      el.style.display = local >= 0 && local < item.timing.durationFrames ? '' : 'none';
      var p = Math.max(0, Math.min(1, local / (item.timing.revealFrames || 1)));
      if (item.timing.reveal === 'wipe') el.style.clipPath = 'inset(0 ' + ((1-p)*100) + '% 0 0)';
      if (item.timing.reveal === 'path') {
        var line = el.querySelector('polyline,path');
        if (line) line.style.strokeDashoffset = String(1-p);
      }
      if (item.timing.reveal === 'words') {
        var words = el.querySelectorAll('[data-res-word]');
        words.forEach(function (word, i) { word.style.opacity = p >= (i+1)/words.length ? '1' : '0'; });
      }
      (item.textSpans || []).forEach(function (span) {
        var targets = Array.from(el.querySelectorAll('[data-res-text-span]')).filter(function (candidate) {
          return candidate.dataset.resTextSpan === span.id;
        });
        if (!targets.length) return;
        var scale = 1;
        if (span.startFrame !== null && span.startFrame !== undefined) {
          var spanLocal = local - span.startFrame;
          var duration = Math.max(1, span.durationFrames || 1);
          if (spanLocal >= 0 && spanLocal < duration && span.profile === 'emphasis') {
            var q = Math.max(0, Math.min(1, spanLocal / Math.max(1, duration - 1)));
            var peak = Number(span.scale || 1);
            scale = q < 0.42 ? 0.92 + (peak - 0.92) * (q / 0.42) : peak + (1 - peak) * ((q - 0.42) / 0.58);
          }
        }
        targets.forEach(function (target) { target.style.transform = 'scale(' + scale + ')'; });
      });
    });
    // Apply handoffs after every layer's frame gate. Motion evaluation restores
    // the declared hierarchy on each seek, so scrubbing backwards is reversible.
    spec.forEach(function (item) {
      if (!item.match) return;
      var el = document.getElementById(item.id);
      var parent = document.getElementById(item.match.parentLayerId);
      var prior = document.getElementById(item.match.previousLayerId);
      if (!el || !parent || !prior) return;
      var frame = seconds * item.timing.fps;
      if (el.dataset.resMatchZ === undefined) el.dataset.resMatchZ = el.style.zIndex;
      if (frame >= item.match.startFrame && frame < item.match.endFrameExclusive) {
        parent.parentElement.appendChild(el);
        el.style.zIndex = '10001';
        prior.style.display = 'none';
      } else {
        if (el.parentElement !== parent) parent.appendChild(el);
        el.style.zIndex = el.dataset.resMatchZ;
      }
    });
    spec.forEach(function (item) {
      if (!item.connector) return;
      var svg = document.getElementById(item.id);
      var from = document.getElementById(item.connector.from);
      var to = document.getElementById(item.connector.to);
      if (!svg || !from || !to) return;
      var a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
      var line = svg.querySelector('polyline,path'), matrix = svg.getScreenCTM();
      svg.style.visibility = a.width && b.width ? '' : 'hidden';
      if (!matrix || !line || !a.width || !b.width) return;
      var inverse = matrix.inverse();
      var start = new DOMPoint(a.x + a.width / 2, a.y + a.height / 2).matrixTransform(inverse);
      var end = new DOMPoint(b.x + b.width / 2, b.y + b.height / 2).matrixTransform(inverse);
      if (line.tagName.toLowerCase() === 'polyline') line.setAttribute('points', start.x+','+start.y+' '+end.x+','+end.y);
      else line.setAttribute('d', 'M '+start.x+' '+start.y+' Q '+start.x+' '+end.y+' '+end.x+' '+end.y);
    });
  };
  window.__resEditorialObserve = function (frame) {
    var root = document.getElementById('root').getBoundingClientRect();
    return spec.map(function (item) {
      var el = document.getElementById(item.id);
      if (!el) return { id: item.id, semanticId: item.semanticId, present: false };
      var rect = el.getBoundingClientRect(), style = getComputedStyle(el);
      var clipped = rect.right <= root.left || rect.bottom <= root.top || rect.left >= root.right || rect.top >= root.bottom;
      var effectiveOpacity = 1, ancestor = el;
      while (ancestor && ancestor !== document.documentElement) {
        effectiveOpacity *= Number(getComputedStyle(ancestor).opacity || 1);
        ancestor = ancestor.parentElement;
      }
      var roiMeasurement = null;
      if (item.regionOfInterest && (el.tagName === 'IMG' || el.tagName === 'VIDEO')) {
        var sourceWidth = el.tagName === 'IMG' ? el.naturalWidth : el.videoWidth;
        var sourceHeight = el.tagName === 'IMG' ? el.naturalHeight : el.videoHeight;
        if (sourceWidth > 0 && sourceHeight > 0 && rect.width > 0 && rect.height > 0) {
          var fit = style.objectFit || 'fill', renderedWidth = rect.width, renderedHeight = rect.height;
          if (fit === 'contain' || fit === 'cover') {
            var factor = fit === 'contain'
              ? Math.min(rect.width / sourceWidth, rect.height / sourceHeight)
              : Math.max(rect.width / sourceWidth, rect.height / sourceHeight);
            renderedWidth = sourceWidth * factor;
            renderedHeight = sourceHeight * factor;
          }
          var mediaLeft = rect.left + (rect.width - renderedWidth) / 2;
          var mediaTop = rect.top + (rect.height - renderedHeight) / 2;
          var roi = item.regionOfInterest;
          var roiRect = {
            left: mediaLeft + roi.x * renderedWidth,
            top: mediaTop + roi.y * renderedHeight,
            width: roi.width * renderedWidth,
            height: roi.height * renderedHeight
          };
          var visibleWidth = Math.max(0, Math.min(roiRect.left + roiRect.width, rect.right, root.right) - Math.max(roiRect.left, rect.left, root.left));
          var visibleHeight = Math.max(0, Math.min(roiRect.top + roiRect.height, rect.bottom, root.bottom) - Math.max(roiRect.top, rect.top, root.top));
          roiMeasurement = {
            method: 'renderer_axis_aligned_object_fit',
            visibleRatio: Math.max(0, Math.min(1, visibleWidth * visibleHeight / Math.max(1, roiRect.width * roiRect.height))),
            sourceWidth: sourceWidth,
            sourceHeight: sourceHeight,
            bounds: {
              x: roiRect.left - root.left,
              y: roiRect.top - root.top,
              width: roiRect.width,
              height: roiRect.height
            }
          };
        }
      }
      return {
        id: item.id,
        semanticId: item.semanticId,
        contentIdentity: item.contentIdentity || null,
        contentReferenceId: item.contentReferenceId || null,
        contentPartId: item.contentPartId || null,
        visualRole: item.visualRole,
        frame: frame,
        present: true,
        visible: style.display !== 'none' && style.visibility !== 'hidden' && effectiveOpacity > 0 && !clipped,
        opacity: effectiveOpacity,
        bounds: {
          x: rect.left - root.left,
          y: rect.top - root.top,
          width: rect.width,
          height: rect.height
        },
        cropIntentional: Boolean(item.cropIntentional),
        regionOfInterest: item.regionOfInterest || null,
        roiMeasurement: roiMeasurement
      };
    });
  };
  window.__resEditorialReady = Promise.all([
    Promise.all(Array.from(document.fonts).map(function(font) { return font.load().catch(function () {
      window.__resEditorialChecks.errors.push('font:' + font.family);
    }); })),
    document.fonts.ready,
    Promise.all(Array.from(document.images).map(function (img) {
      return img.decode().catch(function () { window.__resEditorialChecks.errors.push('image:' + img.id); });
    }))
  ]).then(function () {
    document.fonts.forEach(function (font) {
      if (font.status !== 'loaded') window.__resEditorialChecks.errors.push('font:' + font.family);
    });
    var displays = spec.map(function (item) {
      var el = document.getElementById(item.id);
      var previous = el ? el.style.display : '';
      if (el) el.style.display = '';
      return previous;
    });
    spec.forEach(function (item) {
      var el = document.getElementById(item.id);
      if (!el || !item.text) return;
      if (item.fitText) {
        var minimum = item.minimumFontSize;
        var size = Math.max(minimum, parseFloat(getComputedStyle(el).fontSize));
        el.style.fontSize = size + 'px';
        while (size > minimum && (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)) {
          size = Math.max(minimum, size - 1);
          el.style.fontSize = size + 'px';
        }
      }
      if (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1)
        window.__resEditorialChecks.textOverflow.push(item.id);
      window.__resEditorialChecks.textMeasurements.push({ id: item.id, width: el.clientWidth, height: el.clientHeight,
        contentWidth: el.scrollWidth, contentHeight: el.scrollHeight, fontSize: parseFloat(getComputedStyle(el).fontSize) });
    });
    spec.forEach(function (item, i) { var el = document.getElementById(item.id); if (el) el.style.display = displays[i]; });
    window.__resEditorialChecks.ready = true;
    window.__resEditorialApply(0);
  });
  window.__resEditorialApply(0);
})();
