var useVideoBG = !!document.mozSetImageElement;
var gifs = [];
// Don't keep more than this many gifs in rotation.
var MAX_GIFS = 10;
// If a gif is shorter than this let it loop until it plays at least
// this long.
var MIN_DURATION = 5000;
// Also let gifs loop at least this many times.
var MIN_LOOPS = 2;
var current_gif = -1;
var queue = [];
var loading;
var es = new EventSource("/feed");
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

function preloadNextImage() {
  if (queue.length == 0)
    return;
  var src = queue[0].url;
  var event = "load";
  if (src.substr(0, 18) == "http://i.imgur.com" && useVideoBG)  {
    src = src.substr(0, src.length - 4) + ".mp4";
    loading = document.createElement("video");
    loading.autoplay = true;
    loading.loop = true;
    event = "canplaythrough";
  } else {
    loading = new Image();
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
    }
    loading = null;
    setTimeout(preloadNextImage, 0);
  });
  loading.src = src;
  console.log("preloading %s", loading.src);
  if (current_gif == -1) {
    gifs.push(loading);
    loading.displayed = true;
    loadNextGif();
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
  if (gif instanceof HTMLImageElement) {
    document.body.style.backgroundImage = "url(" + gifs[current_gif].src + ")";
  } else {
    document.mozSetImageElement("videobg", gif);
    document.body.style.backgroundImage = "-moz-element(#videobg)";
  }
  // Let gifs loop at least MIN_LOOPS times, but maybe more if they're short.
  var duration = 0;
  var loops = 0;
  while (duration < MIN_DURATION || loops < MIN_LOOPS) {
    duration += gif.duration_;
    loops++;
  }
  setTimeout(loadNextGif, duration);
}
