/**
 * eTala Premium Components JS - Seamless Zero-Jump AJAX Pagination Handler
 */

function triggerPageUpdateAJAX(urlStr) {
    if (typeof window.updateRecordsTableAJAX === 'function') {
        window.updateRecordsTableAJAX(urlStr);
        return true;
    }
    if (typeof window.updateIllegalTableAJAX === 'function') {
        window.updateIllegalTableAJAX(urlStr);
        return true;
    }
    if (typeof window.updateArchiveTableAJAX === 'function') {
        window.updateArchiveTableAJAX(urlStr);
        return true;
    }
    if (typeof window.updateWorkspaceTableAJAX === 'function') {
        window.updateWorkspaceTableAJAX(urlStr);
        return true;
    }
    if (typeof window.updateUsersTableAJAX === 'function') {
        window.updateUsersTableAJAX(urlStr);
        return true;
    }
    return false;
}

function changePerPage(val) {
    const url = new URL(window.location.href);
    url.searchParams.set('per_page', val);
    url.searchParams.set('page', 1);
    const urlStr = url.toString();

    if (!triggerPageUpdateAJAX(urlStr)) {
        window.location.href = urlStr;
    }
}
window.changePerPage = changePerPage;

function jumpToPage(val, maxPages, pageParam = 'page') {
    const pageNum = parseInt(val, 10);
    const max = parseInt(maxPages, 10);
    if (isNaN(pageNum) || pageNum < 1 || (!isNaN(max) && pageNum > max)) {
        if (typeof window.showToast === 'function') {
            window.showToast('warning', 'Invalid Page', 'Please enter a valid page number between 1 and ' + maxPages);
        } else {
            alert("Please enter a valid page number between 1 and " + maxPages);
        }
        return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set(pageParam, pageNum);
    const urlStr = url.toString();

    if (!triggerPageUpdateAJAX(urlStr)) {
        window.location.href = urlStr;
    }
}
window.jumpToPage = jumpToPage;
