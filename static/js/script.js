// Initialize Swiper instance
const swiper = new Swiper(".article-container", {
    effect: "slide",
    speed: 1200,
    navigation: {
        prevEl: "#slide-prev",
        nextEl: "#slide-next"
    },
    autoplay: {delay: 4000},
    on: {
        reachEnd: () => swiper.autoplay.stop()
    }
});