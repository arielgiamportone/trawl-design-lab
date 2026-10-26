// jsdom informa «en-US»: las pruebas corren en español salvo que una pida otro idioma.
Object.defineProperty(window.navigator, 'language', { value: 'es-AR', configurable: true });
