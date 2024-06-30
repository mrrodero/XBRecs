$(document).ready(function () {
    var csrfToken = $('meta[name="csrf-token"]').attr('content');

    // Hide by default the trash icon
    $('.bin-icon').hide();

    // Convert the string to an integer
    userRating = parseInt(userRating);
    if (userRating) {
        $('.rating-stars .star').each(function (index) {
            if (index < userRating) {
                $(this).removeClass('far').addClass('fas');
            }
        });
        // Show the trash icon
        $('.bin-icon').show();
    }

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
                // Show the trash icon
                $('.bin-icon').show();
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
                csrfmiddlewaretoken: csrfToken,
            },
            success: function (response) {
                console.log(response.message);
                // Hide the trash icon
                $('.bin-icon').hide();
                // Remove the rating
                $('.rating-stars .star').removeClass('fas').addClass('far');
            },
            error: function (xhr, status, error) {
                console.error(xhr.responseText);
            }
        });
    });
});