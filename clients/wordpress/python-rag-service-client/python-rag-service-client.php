<?php
/**
 * Plugin Name: Python RAG Service Client
 * Description: WordPress reference client for the Python RAG Service.
 * Version: 0.2.2
 * Author: Kemi Oyesiku
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-rate-limiter.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-api-client.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-rest-controller.php';

function rag_service_register_rest_routes() {
	$controller = new RAG_Service_REST_Controller();
	$controller->register_routes();
}

register_activation_hook( __FILE__, 'rag_service_install_rate_limit_storage' );
add_action( 'plugins_loaded', 'rag_service_maybe_install_rate_limit_storage' );
add_action( 'rest_api_init', 'rag_service_register_rest_routes' );
add_filter( 'rest_post_dispatch', 'rag_service_send_retry_after' );

/**
 * Render the RAG search and answer interface.
 */
function rag_service_render_client() {
    wp_enqueue_style(
        'rag-service-search',
        plugin_dir_url( __FILE__ ) . 'assets/rag-search.css',
        array(),
        filemtime( plugin_dir_path( __FILE__ ) . 'assets/rag-search.css' )
    );
    wp_enqueue_script(
        'rag-service-search',
        plugin_dir_url( __FILE__ ) . 'assets/rag-search.js',
        array(),
        filemtime( plugin_dir_path( __FILE__ ) . 'assets/rag-search.js' ),
        true
    );

	wp_localize_script(
		'rag-service-search',
		'ragServiceConfig',
		array(
			'searchUrl' => rest_url( 'python-rag-service/v1/search' ),
			'answerUrl' => rest_url( 'python-rag-service/v1/answer' ),
		)
	);

	ob_start();
	?>
	<div class="rag-service-client">
		<form class="rag-service-search-form">
			<label for="rag-service-query">
				Search or ask the documentation
			</label>
            <p class="rag-service-help">
                Search finds relevant passages. Ask generates an answer from the retrieved pages and articles.
            </p>
			<input
				id="rag-service-query"
				class="rag-service-query"
				type="search"
				name="query"
				required
			>

			<div class="rag-service-actions">
				<button
					type="submit"
					data-mode="search"
				>
                Search
				</button>

				<button
					type="submit"
					data-mode="answer"
				>
                Ask
				</button>
			</div>
		</form>

		<div
			class="rag-service-status"
			aria-live="polite"
		></div>

		<div class="rag-service-results"></div>
	</div>
	<?php

	return ob_get_clean();
}
add_shortcode( 'python_rag_service', 'rag_service_render_client' );