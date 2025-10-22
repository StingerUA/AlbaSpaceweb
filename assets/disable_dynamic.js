// Простая библиотека-затычка для отключения форм, ecommerce и карт в статическом экспорте.
// Подключите этот файл в <head> перед основными JS скриптами или внизу страницы.

(function(){
  function safeLog(){
    if(window.console && console.log) console.log.apply(console, arguments);
  }

  // Остановить отправку форм
  function disableForms(){
    document.addEventListener('submit', function(e){
      var form = e.target;
      // если форма имеет data-allow-dynamic, пропускаем
      if(form && form.getAttribute && form.getAttribute('data-allow-dynamic')==='true') return;
      e.preventDefault();
      e.stopImmediatePropagation();
      var msg = document.createElement('div');
      msg.style.background = '#fff3cd';
      msg.style.border = '1px solid #ffeeba';
      msg.style.padding = '12px';
      msg.style.margin = '8px 0';
      msg.style.color = '#856404';
      msg.textContent = 'Форма отключена в статической версии сайта. Свяжитесь с владельцем сайта для отправки данных.';
      if(form && form.parentNode){
        form.parentNode.insertBefore(msg, form);
      }
      safeLog('Blocked form submit for', form);
      return false;
    }, true);
  }

  // Подменить кнопки Add to cart / Buy, удалив обработчики
  function disableEcommerce(){
    document.addEventListener('click', function(e){
      var t = e.target;
      if(!t) return;
      // ищем по атрибутам или классам, часто в экспорте есть data-ecom или ecom-add
      if(t.closest && (t.closest('[data-ecom]') || t.closest('.zyro-ecom') || t.dataset && (t.dataset.ecom || t.dataset.productId))){
        e.preventDefault();
        e.stopImmediatePropagation();
        alert('Ecommerce отключён в статической версии. Информация о товаре остаётся для просмотра.');
        safeLog('Blocked ecommerce action', t);
        return false;
      }
    }, true);
  }

  // Заменить контейнеры карт на картинку-заглушку
  function replaceMaps(){
    // Ищем элементы, которые явно ссылаются на maps.googleapis.com или имеют класс map
    var candidates = document.querySelectorAll('[data-mapid], .zyro-map, iframe[src*="maps.googleapis.com"], iframe[src*="maps.gstatic.com"], img[src*="maps.gstatic.com"]');
    candidates.forEach(function(el){
      try{
        var placeholder = document.createElement('div');
        placeholder.style.background = '#e9ecef';
        placeholder.style.border = '1px solid #ced4da';
        placeholder.style.color = '#495057';
        placeholder.style.padding = '24px';
        placeholder.style.textAlign = 'center';
        placeholder.textContent = 'Карта отключена в статической версии. Свяжитесь с владельцем сайта для настройки карт.';
        el.parentNode && el.parentNode.replaceChild(placeholder, el);
        safeLog('Replaced map element', el);
      }catch(e){
        // ignore
      }
    });
  }

  function init(){
    if(document.readyState === 'loading'){
      document.addEventListener('DOMContentLoaded', function(){
        disableForms();
        disableEcommerce();
        replaceMaps();
      });
    } else {
      disableForms();
      disableEcommerce();
      replaceMaps();
    }
  }

  // Автоматическое подключение: если URL содержит ?static=1, включаем жёстко
  init();

  // Экспорт для отладки
  window.__disableDynamic = {
    replaceMaps: replaceMaps,
    disableForms: disableForms,
    disableEcommerce: disableEcommerce
  };
})();
