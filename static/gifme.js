/* Any copyright is dedicated to the Public Domain.
 * http://creativecommons.org/publicdomain/zero/1.0/ */

var useVideo = document.createElement("video").canPlayType('video/mp4;codecs="avc1.42E01E, mp4a.40.2"') in {"probably": true, "maybe": true} && navigator.userAgent.indexOf("iPhone") == -1;
var gifs = [];
// Don't keep more than this many gifs in rotation.
var MAX_GIFS = 10;
// If a gif is shorter than this let it loop until it plays at least
// this long.
var MIN_DURATION = 5000;
// Also let gifs loop at least this many times.
var MIN_LOOPS = 2;
var current_gif = -1;
var es;
var queue = [];
var loading;

function preloadNextImage() {
  if (queue.length == 0)
    return;
  var src = queue[0].url;
  var event = "load";
  if (src.substr(0, 18) == "http://i.imgur.com" && useVideo)  {
    src = src.substr(0, src.length - 4) + ".mp4";
    loading = document.createElement("video");
    loading.loop = true;
    event = "canplaythrough";
    loading.addEventListener("loadedmetadata", function meta() {
      loading.removeEventListener("loadedmetadata", meta);
      checkLoadImmediately(loading);
    });
  } else {
    loading = new Image();
  }
  function checkLoadImmediately(e) {
    if (current_gif == -1) {
      gifs.push(e);
      e.displayed = true;
      loadNextGif();
    }
  }
  // HTMLMediaElement has .duration...
  loading.duration_ = queue[0].duration;
  loading.addEventListener(event, function doneloading() {
    loading.removeEventListener(event, doneloading);
    queue.shift();
    console.log("loaded %s, duration %d", loading.src, loading.duration_);
    loading.loaded = true;
    if (!loading.displayed) {
      gifs.push(loading);
      // Prune the set of gifs
      while (gifs.length > MAX_GIFS) {
        gifs.shift();
      }
      if (current_gif == -1) {
        loadNextGif();
      }
    }
    loading = null;
    setTimeout(preloadNextImage, 0);
  });
  loading.src = src;
  console.log("preloading %s", loading.src);
  // Can't stick Image in the DOM right away because we need
  // its dimensions to position it.
}

function center(element) {
  if (!element.naturalWidth) {
    if (element instanceof HTMLVideoElement) {
      element.naturalWidth = element.videoWidth;
      element.naturalHeight = element.videoHeight;
    } else {
      element.naturalWidth = element.width;
      element.naturalHeight = element.height;
    }
  }
  var elRatio = element.naturalWidth / element.naturalHeight;
  var winRatio = window.innerWidth / window.innerHeight;
  // Not sure if this is all perfect.
  if (elRatio > winRatio) {
    element.style.width = "100%";
    element.style.height = "auto";
    element.style.position = "absolute";
    var newHeight = window.innerWidth/elRatio;
    element.style.top = (window.innerHeight - newHeight)/2 + "px";
    element.style.margin = "";
  } else {
    element.style.width = "auto";
    element.style.height = "100%";
    element.style.position = "";
    element.style.top = "";
    element.style.margin = "auto";
  }
}

function loadNextGif() {
  if (current_gif == -1) {
    current_gif = 0;
  } else {
    if (gifs.length == 1 || !gifs[current_gif].loaded) {
      // Only one gif or it hasn't fully loaded, don't bother changing.
      setTimeout(loadNextGif, Math.min(5000, gifs[current_gif].duration_));
      return;
    }
    current_gif = (current_gif + 1) % gifs.length;
  }
  var gif = gifs[current_gif];
  console.log("using gif %s", gif.src);
  center(gif);
  var old = document.body.firstChild;
  if (old instanceof HTMLVideoElement) {
    old.pause();
  }
  if (gif instanceof HTMLVideoElement) {
    gif.play();
  }
  document.body.replaceChild(gif, old);
  // Let gifs loop at least MIN_LOOPS times, but maybe more if they're short.
  var duration = 0;
  var loops = 0;
  while (duration < MIN_DURATION || loops < MIN_LOOPS) {
    duration += gif.duration_;
    loops++;
  }
  setTimeout(loadNextGif, duration);
}

addEventListener("DOMContentLoaded", function() {
  center(document.getElementById("i"));
  es = new EventSource("/feed");
  es.addEventListener("gif", function(e) {
    var data = JSON.parse(e.data);
    console.log("got img url %s, duration %d", data.url, data.duration);
    queue.push(data);
    if (queue.length == 1) {
      preloadNextImage();
    }
  });
  es.addEventListener("ping", function(e) {
    console.log("server ping");
  });
});

addEventListener("resize", function() {
  center(document.body.firstChild);
});
