$('.more').hide();

$('.players').click(function () {
  $(this).append('.').delay(3000).append('.').delay(3000).append('.').delay(3000);
  $(this).load('/shared/mc-utils/player-count.php?server=localhost');
});

$('.players').load('/shared/mc-utils/player-count.php?server=localhost');

$('.server').hover(function () {
  $(this).find('.player-count').html('<img src="/img/loading.gif" />');

	var server = $(this).find('.player-count').attr('id');
	// Get player count
	var string = '<hr /><center>' + server + '</b></center>';
  $(this).find('.player-count').load('/shared/mc-utils/player-count.php?server=' + server);

	$(this).find('.more').stop(true,true).slideDown();
}, function() {
	$(this).find('.more').delay(1000).slideUp();
});

$('.kits').hide();
$('.show-kits').click(function () {
  $('.kits').slideToggle();
});

$('.subscription-search').submit(function() {
  $('#subscriptions').html('<img src="/img/loading.gif" />').load('/shared/ajax.subscriptions.php?username=' + $('.username').val(), function() {
    $('#subscriptions');
  });
});

$('form.no-submit').submit(function(event){
  event.preventDefault();
});

$('.walls-leaderboard').load('/shared/ajax.leaderboard.php');

$('.page').live('click', function () {
  if (!$(this).attr('disabled')) {
    $(".walls-leaderboard").load('/shared/ajax.leaderboard?page=' + $(this).attr('id'));
    $(".profile-search").load('/shared/ajax.profiles.php?username=' + $('.name').text() + '&page=' + $(this).attr('id') + "&max=" + $('.name').attr('id'));
  }
});


$('.search').click(function () {
  $('.search-form').slideToggle();
  $('.search-username').focus();
});

$.fn.exists = function () {
    return this.length !== 0;
}

$('.search-form').submit(function (event) {
  event.preventDefault();
  var url = $('.search-username').val();
  window.location = 'http://mczone.co/user/' + url;
});


$('.profile-search').load('/shared/ajax.profiles.php?username=' + $('.name').text() + "&max=" + $('.name').attr('id'));
