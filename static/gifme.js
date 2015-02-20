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
  loading = new Image();
  loading.onload = function() {
    queue.shift();
    console.log("loaded %s", loading.src);
    gifs.push(loading);
    loading = null;
    if (current_gif == -1) {
      loadNextGif();
    }
    setTimeout(preloadNextImage, 0);
  };
  loading.src = queue[0];
  console.log("preloading %s", loading.src);
}

function loadNextGif() {
  if (current_gif == -1) {
    current_gif = 0;
  } else {
    current_gif = (current_gif + 1) % gifs.length;
  }
  document.body.style.backgroundImage = "url(" + gifs[current_gif].src + ")";
  // TODO: use duration
  setTimeout(loadNextGif, 10000);
}
