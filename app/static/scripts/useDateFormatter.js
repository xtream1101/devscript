dayjs.extend(window.dayjs_plugin_relativeTime)

export default function useDateFormatter() {
  const timestampAttribute = "data-timestamp";
  const formatAttribute = "data-timestamp-format";
  const titleFormatAttribute = "data-timestamp-title-format";
  const DEFAULT_FORMAT = "fromNow";
  const DEFAULT_TITLE_FORMAT = "dddd, MMMM D, YYYY h:mm A";

  function format() {
    const $datetimeElements = document.querySelectorAll(`[${timestampAttribute}]`);
    if ($datetimeElements.length === 0) {
      return;
    }

    for (let i = 0; i < $datetimeElements.length; i++) {
      const $element = $datetimeElements[i];
      const timestamp = $element.getAttribute(timestampAttribute);
      const datetime = dayjs(timestamp);
      const displayFormat =
        $element.getAttribute(formatAttribute) || DEFAULT_FORMAT;
      const titleFormat = $element.getAttribute(titleFormatAttribute) || DEFAULT_TITLE_FORMAT;

      const formattedDate =
        displayFormat === "fromNow"
          ? datetime.fromNow()
          : datetime.format(displayFormat);

      const formattedTitle = datetime.format(titleFormat);
      $element.innerText = formattedDate;
      $element.title = formattedTitle;
    }
  }

  return {
    format,
  };
}
