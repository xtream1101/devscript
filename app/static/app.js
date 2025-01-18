function scrollToSelectedSnippet() {
  const locationQueryParams = new URLSearchParams(window.location.search);
  const selectedSnippetId = locationQueryParams.get('selected_id');

  setTimeout(() => {
    if (selectedSnippetId && !document.location.hash) {
      document.getElementById(`snippet-${selectedSnippetId}`).scrollIntoView({
        behavior: 'instant',
        block: 'center',
        inline: 'center',
      });
    }
  }, 0)
}

function initHLJS() {
  hljs.addPlugin(
    new CopyButtonPlugin({
      autohide: false, // Always show the copy button
    })
  );

  document.querySelectorAll('pre code').forEach((block) => {
    hljs.highlightBlock(block);
  });
}

function initCopyToClipboard() {
  document.querySelectorAll('[data-copy-to-cliboard]').forEach((element) => {
    element.addEventListener('click', (e) => {
      copyToClipboard(e, element.getAttribute('data-copy-to-cliboard'));
    });
  });
}

function copyToClipboard(e, copyElementId) {
  e.preventDefault();
  e.stopPropagation();

  const $btn = e.currentTarget || e.target;
  const $copyElement = document.getElementById(copyElementId);

  if (typeof $copyElement === 'undefined' || $copyElement === null) {
    return;
  }

  const content = $copyElement.value;

  navigator.clipboard.writeText(content).then(() => {
    const originalBtnContents = $btn.innerHTML;
    $btn.classList.add('!bg-green-400');
    $btn.innerText = 'Copied!';

    setTimeout(() => {
      $btn.classList.remove('!bg-green-400');
      $btn.innerHTML = originalBtnContents;
    }, 1000);
  })
}

function initToggleSnippetFavorite() {
  document.querySelectorAll('[data-favorite-btn]').forEach((element) => {
    element.addEventListener('click', (e) => {
      const $btn = e.currentTarget;
      const snippetId = $btn.getAttribute('data-favorite-btn');
      toggleSnippetFavorite(e, snippetId);
    });
  });
}

function toggleSnippetFavorite(e, snippet_id) {
  e.stopPropagation();
  e.preventDefault();

  const $btns = document.querySelectorAll(`[data-favorite-btn="${snippet_id}"]`);

  const url = `/snippets/${snippet_id}/toggle-favorite/`;
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  })
    .then(response => response.json())
    .then(data => {
      if (data.is_favorite) {
        $btns.forEach(($btn) => {
          $btn.classList.add('is-favorite');
          $btn.title = 'Remove from favorites';
        });
      } else {
        $btns.forEach(($btn) => {
          $btn.classList.remove('is-favorite');
          $btn.title = 'Add to favorites';
        });
      }
    })
    .catch((error) => {
      console.error('Error:', error);
    });
}

function initKeyboardShortcuts() {
  document.body.addEventListener("keyup", function (event) {
    if (event.target !== document.body) {
      return;
    }

    const SEARCH_KEY = '/';
    const ADD_KEY = 'a';
    const SUPPORTED_SHORTCUTS = [SEARCH_KEY, ADD_KEY];
    if (!SUPPORTED_SHORTCUTS.includes(event.key)) {
      return;
    }

    if (event.key === SEARCH_KEY) {
      const $searchInput = document.getElementById('global-search-input');
      if (!$searchInput) {
        return;
      }
      $searchInput.focus();
    } else if (event.key === ADD_KEY) {
      const $addSnippetBtn = document.getElementById('global-add-snippet-btn');
      if (!$addSnippetBtn) {
        return;
      }
      $addSnippetBtn.click();
    }
  });
}

function initMarkdownEditor() {
  const $textareas = document.querySelectorAll('[data-markdown-editor]');
  if ($textareas.length === 0) {
    return;
  }

  for (let i = 0; i < $textareas.length; i++) {
    const $textarea = $textareas[i];
    $textarea.style.display = 'none';

    const $editor = document.createElement('div');
    $textarea.parentNode.insertBefore($editor, $textarea);

    const editor = new toastui.Editor({
      el: $editor,
      height: '500px',
      initialValue: $textarea.value,
      previewStyle: 'tab',
      previewHighlight: false,
      plugins: [],
      hideModeSwitch: true,
      autofocus: false,
      events: {
        change: function () {
          $textarea.value = editor.getMarkdown();
        },
      },
    });
  }
}

function initTags() {
  const $tagInputs = document.querySelectorAll('[data-tags-input]')
  if ($tagInputs.length === 0) {
    return;
  }

  for (let i = 0; i < $tagInputs.length; i++) {
    const $input = $tagInputs[i];
    new Tagify($input, {
      keepInvalidTags: true,
      originalInputValueFormat: valuesArr => valuesArr.map(item => item.value).join(', ')
    })
  }
}

function initDateFormatter() {
  const $datetimeElements = document.querySelectorAll('[data-timestamp]');
  if ($datetimeElements.length === 0) {
    return;
  }

  for (let i = 0; i < $datetimeElements.length; i++) {
    const $element = $datetimeElements[i];
    const datetime = dayjs($element.getAttribute('data-timestamp'));
    const displayFormat = $element.getAttribute('data-timestamp-format') || 'fromNow';
    const titleFormat = $element.getAttribute('data-timestamp-title-format') || 'dddd, MMMM D, YYYY h:mm A';

    const formattedDate = (displayFormat === 'fromNow') ? datetime.fromNow() : datetime.format(displayFormat);
    const formattedTitle = datetime.format(titleFormat);

    $element.innerText = formattedDate;
    $element.title = formattedTitle;
  }
}

document.addEventListener('DOMContentLoaded', (event) => {
  scrollToSelectedSnippet();
  initDateFormatter();
  initHLJS();
  initMarkdownEditor();
  initTags();
  initCopyToClipboard();
  initToggleSnippetFavorite();
  initKeyboardShortcuts();
});
