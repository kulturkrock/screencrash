'use strict'

function addClass(element, name) {
    if (element.className.length === 0) {
        element.className = name;
    } else {
        element.className += ` ${name}`;
    }
}

function removeClass(element, name) {
    /* Note for the regex:
        We need both ' name' and 'name ' since matches can't overlap.
        This means that if we have the class name "test test test2"
        we want to match with both "^test " and "test " (" test" would
        not give us a match here since there is overlap).
    */
    const re = `^${name}$|^${name} | ${name}|${name} `;
    element.className = element.className.replace(new RegExp(re, 'g'), '');
}

function hasClass(element, name) {
    const re = `^${name}$|^${name} | ${name}|${name} `;
    return new RegExp(re, 'g').test(element.className);
}

function createImage(message) {
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
        removeClass(wrapper, "hidden");
    } else {
        addClass(wrapper, "hidden");
    }
}

function subscribe() {
    const eventSource = new EventSource("../api/subscribe");
    eventSource.addEventListener("message", event => {
        const message = JSON.parse(event.data);
        if (message.command && message.type === "image") {
            createImage(message);
        }
    })
}

subscribe();