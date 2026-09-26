<?php
/**
 * Plugin Name: Python RAG Service Client
 * Description: WordPress reference client for the Python RAG Service.
 * Version: 0.1.0
 * Author: Kemi Oyesiku
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-api-client.php';
require_once plugin_dir_path( __FILE__ ) . 'includes/class-rag-rest-controller.php';

function rag_service_register_rest_routes() {
	$controller = new RAG_Service_REST_Controller();
	$controller->register_routes();
}

add_action( 'rest_api_init', 'rag_service_register_rest_routes' );

/**
 * Render the RAG search and answer interface.
 */
function rag_service_render_client() {
    wp_enqueue_style(
        'font-awesome-5',
        plugins_url( 'otter-blocks/assets/fontawesome/css/all.min.css' ),
        array()
    );
    wp_enqueue_style(
        'rag-service-search',
        plugin_dir_url( __FILE__ ) . 'assets/rag-search.css',
        array( 'font-awesome-5' ),
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
                <i class="fas fa-search"></i> Search
				</button>

				<button
					type="submit"
					data-mode="answer"
				>
                <i class="far fa-question-circle"></i> Ask
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