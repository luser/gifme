var useVideoBG = !!document.mozSetImageElement;
var gifs = [];
var current_gif = -1;
var queue = [];
var loading;
var es = new EventSource("/feed");
es.addEventListener("gif", function(e) {
  var data = JSON.parse(e.data);
  console.log("got img url %s", data.url);
  // TODO: use duration
  queue.push(data.url);
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
  var src = queue[0];
  var event = "load";
  if (src.substr(0, 18) == "http://i.imgur.com" && useVideoBG)  {
    src = src.substr(0, src.length - 4) + ".webm";
    loading = document.createElement("video");
    loading.autoplay = true;
    loading.loop = true;
    event = "canplaythrough";
  } else {
    loading = new Image();
  }
  loading.addEventListener(event, function doneloading() {
    loading.removeEventListener(event, doneloading);
    queue.shift();
    console.log("loaded %s", loading.src);
    if (!loading.displayed) {
      gifs.push(loading);
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
    if (gifs.length == 1) {
      // Only one gif, don't bother changing.
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
  // TODO: use duration
  setTimeout(loadNextGif, 10000);
}
