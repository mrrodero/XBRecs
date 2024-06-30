$(document).ready(function () {
    var csrfToken = $('meta[name="csrf-token"]').attr('content');
    // Handle star rating click
    $('.rating-stars .star').click(function () {
        var index = $(this).data('index');
        var bookId = $(this).closest('.rating').attr('id');

        // Highlight the selected stars
        $(this).siblings('.star').removeClass('far').addClass('fas');
        $(this).prevAll('.star').removeClass('far').addClass('fas');
        $(this).addClass('fas');
        $(this).nextAll('.star').removeClass('fas').addClass('far');

        // AJAX to save the rating
        $.ajax({
            method: 'POST',
            url: '/application/book-rate/' + bookId + '/',
            data: {
                csrfmiddlewaretoken: csrfToken,
                rating: index
            },
            success: function (response) {
                console.log(response.message);
            },
            error: function (xhr, status, error) {
                console.error(xhr.responseText);
            }
        });
    });

    // Handle trash icon click
    $('.bin-icon').click(function () {
        var bookId = $(this).closest('.rating').attr('id');

        // AJAX to delete the rating
        $.ajax({
            method: 'POST',
            url: '/application/book-rate-remove/' + bookId + '/',
            data: {
                csrfmiddlewaretoken: '{{ csrf_token }}',
            },
            success: function (response) {
                console.log(response.message);
                // Remove the whole book entry
                $('#book-entry-' + bookId).remove();
            },
            error: function (xhr, status, error) {
                console.error(xhr.responseText);
            }
        });
    });
});