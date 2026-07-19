/**
 * ERARMS Premium Components JS
 */

function changePerPage(val) {
    const url = new URL(window.location.href);
    url.searchParams.set('per_page', val);
    url.searchParams.set('page', 1); // Reset to page 1 when changing page size
    window.location.href = url.toString();
}

function jumpToPage(val, maxPages) {
    const pageNum = parseInt(val);
    if (isNaN(pageNum) || pageNum < 1 || pageNum > maxPages) {
        alert("Please enter a valid page number between 1 and " + maxPages);
        return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set('page', pageNum);
    window.location.href = url.toString();
}
