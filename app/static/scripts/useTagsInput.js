export default function useTagsInput() {
  function setup() {
    const $tagInputs = document.querySelectorAll("[data-tags-input]");
    if ($tagInputs.length === 0) {
      return;
    }

    for (let i = 0; i < $tagInputs.length; i++) {
      const $input = $tagInputs[i];
      const $tagify = new Tagify($input, {
        pattern: /^[a-zA-Z0-9\.\-\_\s\\\/]{0,16}$/i,
        keepInvalidTags: true,
        originalInputValueFormat: (valuesArr) =>
          valuesArr.map((item) => item.value).join(","),
      });
      new DragSort($tagify.DOM.scope, {
        selector: '.' + $tagify.settings.classNames.tag,
        callbacks: {
          dragEnd() {
            $tagify.updateValueByDOMTags();
          }
        }
      })
    }
  }

  return {
    setup,
  };
}
