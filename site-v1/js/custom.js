// SET CAROUSEL
$('.carousel').carousel({
    interval: 5000
  })

// PLAYER SEARCH
$(".player-container").css({opacity: "0.7"});
$(".player-container").hover(function() {
    $(this).stop().animate({opacity: "1.0"}, 200);
  },
  function() {
    $(this).stop().animate({opacity: "0.8"}, 200);
  });

// CURRENT PLAYERS
$(".walls-players").hide().load("/includes/players.php?server=walls", function() {
  $(this).append(' players');
  $(this).show();
});
$(".hg-players").hide().load("/includes/players.php?server=hg", function() {
  $(this).append(' players');
  $(this).show();
});
$(".kitpvp-players").hide().load("/includes/players.php?server=kitpvp", function() {
  $(this).append(' players');
  $(this).show();
});

// TERRASCAPE UPGRADE FORM
$('.upgrade').hide();
$('.show-upgrade').click(function() {
  $('.upgrade').slideToggle();
});

// ENSURE DONATION VALIDITY
$("form.donation").submit(function(){
    var isFormValid = true;
    $(this).find('input').each(function(){
        if ($.trim($(this).val())=="Username"){
            $(this).addClass("highlight");
            isFormValid = false;
        }
        else{
            $(this).removeClass("highlight");
        }
    });
    if (!isFormValid) alert("Please fill in your username!");
    return isFormValid;
});

// SUBSCRIPTION SEARCH
$('.subscription-search').submit(function() {
  $('#subscriptions').html('<img src="/img/ajax-loader.gif" />').load('/includes/subscriptions.php?username=' + $('.username').val(), function() {
    $('#subscriptions');
  });
});



// LOAD USER MODAL
$('#myModal').modal();
$('#myModal').modal('hide');
$('.user-modal').click(function() {
	$('#myModal').load('/includes/user-modal.php?username=' + $(this).find('h3').text()).modal();
});
$('.player-link').click(function() {
	$('#myModal').load('/includes/user-modal.php?username=' + $(this).text()).fadeIn();
});


// PLAYER LEADERBOARDS
$('#walls_top').hide().load('/includes/top/walls.php').fadeIn(700);
$('#hg_top').hide().load('/includes/top/hg.php').fadeIn(700);
$('#kitpvp_top').hide().load('/includes/top/kitpvp.php').fadeIn(700);
$('#all_top').hide().load('/includes/top/all.php').fadeIn(700);
// CLICK FUNCTIONS
$('#walls_tabs li a').click(function () {
	$('#walls_top').hide().load("/includes/top/walls.php?order=" + $(this).attr('href').replace('#','')).fadeIn(400);
});
$('#hg_tabs li a').click(function () {
  $('#hg_top').hide().load("/includes/top/hg.php?order=" + $(this).attr('href').replace('#','')).fadeIn(400);
});
$('#kitpvp_tabs li a').click(function () {
  $('#kitpvp_top').hide().load("/includes/top/kitpvp.php?order=" + $(this).attr('href').replace('#','')).fadeIn(400);
});
$('#all_tabs li a').click(function () {
  $('#all_top').hide().load("/includes/top/all.php?order=" + $(this).attr('href').replace('#','')).fadeIn(400);
});


// CANCEL ENTER ON KIT SEARCH
$('form.kit-search').submit(function(event){
  event.preventDefault();
});
// CANCEL ENTER ON SUBMIT
$('form.no-submit').submit(function(event){
  event.preventDefault();
});

// KIT PACKAGE SEARCH
$('input.wks').keyup(function (e) {
	var value = $(this).val();
	if ((jQuery.trim(value)).length==0)
		$('.walls-packages').load('/includes/packages/walls.php');
	else
	$('.walls-packages').load('/includes/packages/walls.php?search=' + encodeURIComponent(value));
});
$('input.hgks').keyup(function (e) {
  var value = $(this).val();
  if ((jQuery.trim(value)).length==0)
    $('.hg-packages').load('/includes/packages/hg.php');
  else
  $('.hg-packages').load('/includes/packages/hg.php?search=' + encodeURIComponent(value));
});
$('input.kpks').keyup(function (e) {
  var value = $(this).val();
  if ((jQuery.trim(value)).length==0)
    $('.kitpvp-packages').load('/includes/packages/kitpvp.php');
  else
  $('.kitpvp-packages').load('/includes/packages/kitpvp.php?search=' + encodeURIComponent(value));
});


window.setInterval(loadservers, 5000);
function loadservers() {
	if (location.pathname.indexOf("walls") >= 0) {
	 $('.servers').load('/includes/servers.php?server=walls');
	}
	else if (location.pathname.indexOf("hg") >= 0) {
	 $('.servers').load('/includes/servers.php?server=hg');
	}
	else if (location.pathname.indexOf("kitpvp") >= 0) {
	 $('.servers').load('/includes/servers.php?server=kitpvp');
	}
}

$('.walls-servers').load('/includes/servers.php?server=walls');
$('.hg-servers').load('/includes/servers.php?server=hg');
$('.kitpvp-servers').load('/includes/servers.php?server=kitpvp');


// IE9 PLACEHOLDERS
$('[placeholder]').focus(function() {
  var input = $(this);
  if (input.val() == input.attr('placeholder')) {
    input.val('');
    input.removeClass('placeholder');
  }
}).blur(function() {
  var input = $(this);
  if (input.val() == '' || input.val() == input.attr('placeholder')) {
    input.addClass('placeholder');
    input.val(input.attr('placeholder'));
  }
}).blur();