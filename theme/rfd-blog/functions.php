<?php
/**
 * RFD Blog child theme (parent: Twenty Twenty-Five).
 *
 * Carries the office tokens onto the blog and maps post categories onto the
 * two lanes — consulting and building — so cards and CTAs colour themselves.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Enqueue parent Twenty Twenty-Five stylesheet first, then the child
 * stylesheet as its dependent — the standard child-theme pattern.
 */
add_action( 'wp_enqueue_scripts', 'rfd_blog_enqueue_styles' );
function rfd_blog_enqueue_styles() {
	wp_enqueue_style(
		'twentytwentyfive-style',
		get_template_directory_uri() . '/style.css',
		array(),
		wp_get_theme( 'twentytwentyfive' )->get( 'Version' )
	);
	wp_enqueue_style(
		'rfd-blog-style',
		get_stylesheet_uri(),
		array( 'twentytwentyfive-style' ),
		wp_get_theme()->get( 'Version' )
	);
}

/**
 * Map a category slug to its lane: 'consulting', 'building', or null.
 * Lists from the redesign plan's section 4.1, slugified.
 */
function rfd_lane( string $category_slug ): ?string {
	static $map = array(
		'contact-center'    => 'consulting',
		'convoso'           => 'consulting',
		'dnc-compliance'    => 'consulting',
		'dialer-ops'        => 'consulting',
		'sheets-automation' => 'consulting',
		'dev-notes'         => 'building',
		'games'             => 'building',
		'agents-automation' => 'building',
		'sessions'          => 'building',
	);
	return $map[ $category_slug ] ?? null;
}

/**
 * Lane of a post's primary category (first category that maps).
 */
function rfd_post_lane( int $post_id ): ?string {
	$categories = get_the_category( $post_id );
	if ( ! $categories ) {
		return null;
	}
	foreach ( $categories as $category ) {
		$lane = rfd_lane( $category->slug );
		if ( null !== $lane ) {
			return $lane;
		}
	}
	return null;
}

/**
 * Add lane-consulting / lane-building to <body> when the current post or
 * category archive maps to a lane (drives the lane-cta-* pattern visibility).
 */
add_filter( 'body_class', 'rfd_blog_body_class' );
function rfd_blog_body_class( array $classes ): array {
	$lane = null;
	if ( is_singular() ) {
		$lane = rfd_post_lane( get_the_ID() );
	} elseif ( is_category() ) {
		$queried = get_queried_object();
		if ( $queried instanceof WP_Term ) {
			$lane = rfd_lane( $queried->slug );
		}
	}
	if ( null !== $lane ) {
		$classes[] = 'lane-' . $lane;
	}
	return $classes;
}

/**
 * Add the lane class per post so a card template calling
 * post_class( 'arcade-card' ) renders class="arcade-card lane-consulting"
 * (or lane-building) with no per-post inline style.
 */
add_filter( 'post_class', 'rfd_blog_post_class', 10, 3 );
function rfd_blog_post_class( array $classes, array $css_class, int $post_id ): array {
	$lane = rfd_post_lane( $post_id );
	if ( null !== $lane ) {
		$classes[] = 'lane-' . $lane;
	}
	return $classes;
}
