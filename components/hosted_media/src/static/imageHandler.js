import domUtils from "./domUtils.js";


function create(message) {
    const wrapper = document.createElement('div');
    wrapper.id = message.entityId;
    if (message.visible) {
        wrapper.className = 'media-wrapper';
    } else {
        wrapper.className = 'media-wrapper hidden';
    }
    const html = `<img id = 'image-${message.entityId}' class = 'image-media' src = '/assets/${message.asset}'>`
    wrapper.innerHTML = html;
    document.body.appendChild(wrapper);

}

function setVisible(entityId, visible) {
    const wrapper = document.getElementById(entityId);
    if (visible){
        domUtils.removeClass(wrapper, "hidden");
    } else {
        domUtils.addClass(wrapper, "hidden");
    }
}

export default { create, setVisible }