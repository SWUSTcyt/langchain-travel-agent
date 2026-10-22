/* 地图容器固定在页面上。行程 JSON 放在 #trip-map-payload 里，变了就拆掉旧图重画。 */
(function () {
  var map = null;
  var overlays = [];
  var lastRaw = null;
  var selectedDay = 0;

  function payloadNode() {
    return document.querySelector("#trip-map-payload textarea");
  }

  function readRaw() {
    var node = payloadNode();
    return node ? (node.value || "") : "";
  }

  function publish() {
    var center = null;
    try {
      var point = map && map.getCenter && map.getCenter();
      if (point) center = [point.getLng(), point.getLat()];
    } catch (err) {
      center = null;
    }
    var legend = document.getElementById("trip-map-legend");
    var card = document.getElementById("ta-map-card");
    window.__tripMapStatus = {
      overlayCount: overlays.length,
      lineCount: overlays.filter(function (item) { return item && item.__tripLine; }).length,
      legend: legend ? legend.textContent : "",
      center: center,
      cardOff: card ? card.classList.contains("map-off") : true
    };
  }

  function setLegend(text) {
    var legend = document.getElementById("trip-map-legend");
    if (legend) legend.textContent = text || "";
  }

  function setCardVisible(show) {
    var card = document.getElementById("ta-map-card");
    if (card) card.classList.toggle("map-off", !show);
  }

  function destroyMap() {
    overlays = [];
    if (map) {
      try { map.destroy(); } catch (err) { /* 旧图拆不掉就丢掉引用 */ }
      map = null;
    }
    var el = document.getElementById("trip-map");
    if (el) el.innerHTML = "";
  }

  var infoWindow = null;

  function markerHtml(stop, color) {
    return '<div class="map-pin"><i style="background:' + color + '">' + stop.order + "</i></div>";
  }

  function esc(value) {
    return String(value || "").replace(/[&<>"]/g, function (ch) {
      return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch];
    });
  }

  function popupHtml(stop, isEnd) {
    var head = esc(stop.order + " · " + (stop.name || ""));
    var from = esc(stop.from || "上一站");
    var move = stop.order === 1
      ? "起点，下一站从这里出发"
      : (isEnd ? "终点 · 从 " + from + " 过来" : "从 " + from + " 过来");
    var extra = stop.slot ? " · " + esc(stop.slot) : "";
    var how = stop.how ? "<p>" + esc(stop.how) + "</p>" : "";
    return '<div class="map-pop"><b>' + head + extra + "</b><p>" + move + "</p>" + how + "</div>";
  }

  function addLine(path, color) {
    var line = new AMap.Polyline({
      path: path,
      strokeColor: color,
      strokeWeight: 6,
      strokeOpacity: 0.95,
      zIndex: 180,
      lineJoin: "round"
    });
    line.__tripLine = true;
    map.add(line);
    overlays.push(line);
  }

  function draw(payload, dayIndex) {
    if (!payload || !payload.available || !window.AMap) return;
    var el = document.getElementById("trip-map");
    if (!el) return;
    var days = payload.days || [];
    var day = days[dayIndex] || {};
    var stops = day.stops || [];
    var first = null;
    days.forEach(function (item) {
      (item.stops || []).forEach(function (stop) {
        if (!first) first = stop;
      });
    });
    if (!first) return;
    if (!map) {
      map = new AMap.Map(el, {
        zoom: 13,
        center: [first.lng, first.lat],
        resizeEnable: true
      });
    }
    overlays.forEach(function (item) { map.remove(item); });
    overlays = [];
    var selectedMarkers = [];
    days.forEach(function (item, index) {
      var dayStops = item.stops || [];
      var dayColor = item.color || "#0f7c9c";
      dayStops.forEach(function (stop, stopIndex) {
        var selected = index === dayIndex;
        var isEnd = stopIndex === dayStops.length - 1 && dayStops.length > 1;
        var wrap = document.createElement("div");
        wrap.innerHTML = markerHtml(stop, dayColor);
        var pin = wrap.firstElementChild || wrap;
        var marker = new AMap.Marker({
          position: [stop.lng, stop.lat],
          title: (stop.order || stopIndex + 1) + " " + stop.name,
          content: pin,
          anchor: "center",
          opacity: selected ? 1 : 0.92,
          zIndex: selected ? 130 : 60
        });
        function openTip() {
          var root = payload.turnId
            ? document.querySelector('.turn-card[data-turn="' + payload.turnId + '"]')
            : document;
          selectDay(payload, index, stop.id, root);
          if (!infoWindow) infoWindow = new AMap.InfoWindow({ offset: new AMap.Pixel(0, -12) });
          infoWindow.setContent(popupHtml(stop, isEnd));
          infoWindow.open(map, [stop.lng, stop.lat]);
        }
        pin.addEventListener("click", function (event) {
          event.stopPropagation();
          openTip();
        });
        marker.on("click", openTip);
        map.add(marker);
        overlays.push(marker);
        if (selected) selectedMarkers.push(marker);
      });
    });
    var path = (day.path && day.path.length >= 2)
      ? day.path
      : stops.map(function (stop) { return [stop.lng, stop.lat]; });
    var dayColor = day.color || "#0f7c9c";
    if (stops.length >= 2 && path.length >= 2) addLine(path, dayColor);
    var names = stops.map(function (stop) { return stop.name; }).join(" → ");
    var dayLine = path.length >= 2
      ? "第 " + (dayIndex + 1) + " 天 · " + names
      : "第 " + (dayIndex + 1) + " 天只有 " + stops.length + " 个点，所以没有线。";
    var asked = payload.question ? String(payload.question) : "";
    if (asked.length > 18) asked = asked.slice(0, 18) + "…";
    setLegend(asked ? asked + " · " + dayLine : dayLine);
    if (map.stopAnimation) map.stopAnimation();
    if (stops.length === 1) {
      map.setZoomAndCenter(12, [stops[0].lng, stops[0].lat], true);
    } else if (selectedMarkers.length) {
      map.setFitView(selectedMarkers, true, [72, 72, 72, 72]);
    }
    publish();
  }

  function selectDay(payload, dayIndex, stopId, root) {
    selectedDay = dayIndex;
    var scope = root && root.querySelectorAll ? root : document;
    if (payload && payload.turnId) {
      document.querySelectorAll(".turn-card").forEach(function (card) {
        card.setAttribute("data-selected", card.getAttribute("data-turn") === payload.turnId ? "true" : "false");
      });
    }
    scope.querySelectorAll("[data-day]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", String(Number(btn.getAttribute("data-day")) === dayIndex));
    });
    var dayKey = (payload && payload.turnId ? payload.turnId + "-" : "") + "day-" + dayIndex;
    scope.querySelectorAll("section.day").forEach(function (sec) {
      sec.classList.toggle("faded", sec.id !== dayKey);
    });
    if (payload && payload.available) draw(payload, dayIndex);
    scope.querySelectorAll(".stop.hit").forEach(function (node) {
      node.classList.remove("hit");
    });
    if (!stopId) return;
    var row = document.getElementById(stopId);
    if (!row) return;
    row.classList.add("hit");
    row.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function findDayButton(event) {
    var path = event.composedPath ? event.composedPath() : [event.target];
    for (var i = 0; i < path.length; i++) {
      var node = path[i];
      if (node && node.getAttribute && node.getAttribute("data-day") != null) return node;
    }
    return null;
  }

  document.addEventListener("click", function (event) {
    var path = event.composedPath ? event.composedPath() : [event.target];
    for (var i = 0; i < path.length; i++) {
      var node = path[i];
      if (!node || !node.getAttribute) continue;
      var fill = node.getAttribute("data-fill");
      if (!fill) continue;
      var input = document.querySelector("#ta-input textarea");
      if (!input) return;
      input.value = fill;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      return;
    }
    var btn = findDayButton(event);
    if (btn) {
      var card = btn.closest ? btn.closest(".turn-card") : null;
      var box = card ? card.querySelector(".turn-map") : null;
      var raw = box ? box.value : readRaw();
      if (!raw) return;
      try {
        selectDay(JSON.parse(raw), Number(btn.getAttribute("data-day")), null, card || document);
      } catch (err) { /* 数据还不是完整 JSON */ }
      return;
    }
    var path2 = event.composedPath ? event.composedPath() : [event.target];
    var turnCard = null;
    for (var j = 0; j < path2.length; j++) {
      var host = path2[j];
      if (host && host.classList && host.classList.contains("turn-card")) {
        turnCard = host;
        break;
      }
    }
    if (!turnCard || turnCard.getAttribute("data-selected") === "true") return;
    var stored = turnCard.querySelector(".turn-map");
    if (!stored || !stored.value) return;
    try {
      selectDay(JSON.parse(stored.value), 0, null, turnCard);
    } catch (err2) { /* 这张卡没有可画的坐标 */ }
  }, true);

  function drawDefault(payload) {
    setCardVisible(true);
    setLegend((payload && payload.message) || "还没有地点。");
    if (!window.AMap) {
      publish();
      return;
    }
    var el = document.getElementById("trip-map");
    if (!el) return;
    var center = (payload && payload.center) || [104.2, 35.8];
    var zoom = (payload && payload.zoom) || 4;
    if (!map) {
      map = new AMap.Map(el, {
        zoom: zoom,
        center: center,
        resizeEnable: true
      });
    }
    overlays.forEach(function (item) { map.remove(item); });
    overlays = [];
    if (infoWindow) {
      try { infoWindow.close(); } catch (err) { /* 没有打开的气泡 */ }
    }
    if (map.stopAnimation) map.stopAnimation();
    map.setZoomAndCenter(zoom, center, true);
    if (map.resize) map.resize();
    publish();
  }

  function renderFromRaw(raw) {
    if (!raw) {
      drawDefault({ message: "还没有地点。", center: [104.2, 35.8], zoom: 4 });
      return;
    }
    var payload;
    try {
      payload = JSON.parse(raw);
    } catch (err) {
      return;
    }
    if (!payload.available) {
      destroyMap();
      setCardVisible(true);
      setLegend(payload.message || "地图暂不可用");
      var slot = document.getElementById("trip-map");
      if (slot) slot.textContent = payload.message || "地图暂不可用";
      publish();
      return;
    }
    if (!window.AMap) return;
    var days = payload.days || [];
    var any = days.some(function (day) { return (day.stops || []).length; });
    if (!any) {
      drawDefault(payload);
      return;
    }
    setCardVisible(true);
    selectedDay = Number(payload.selectedDay || 0);
    draw(payload, selectedDay);
    if (map && map.resize) map.resize();
  }

  setInterval(function () {
    var raw = readRaw();
    if (raw === lastRaw) return;
    if (raw && !window.AMap) {
      try {
        if (JSON.parse(raw).available) return;
      } catch (err) {
        return;
      }
    }
    try {
      renderFromRaw(raw);
      lastRaw = raw;
    } catch (err) {
      setCardVisible(true);
      setLegend("地图绘制失败：" + (err && err.message ? err.message : err));
      publish();
    }
  }, 400);
})();
