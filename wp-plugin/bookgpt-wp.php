<?php
/**
 * The plugin bootstrap file
 *
 * @wordpress-plugin
 * Plugin Name:       BookGPT for WordPress
 * Plugin URI:        https://github.com/yourusername/bookgptwp
 * Description:       Integrate BookGPT AI book recommendations with analytics, API monitoring, and Amazon affiliate integration.
 * Version:           1.0.0
 * Author:            Your Name
 * License:           GPL-2.0+
 * License URI:       http://www.gnu.org/licenses/gpl-2.0.txt
 * Text Domain:       bookgpt-wp
 * Domain Path:       /languages
 */

// If this file is called directly, abort.
if (!defined('WPINC')) {
    die;
}

// Define plugin constants
define('BOOKGPT_VERSION', '1.0.0');
define('BOOKGPT_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('BOOKGPT_PLUGIN_URL', plugin_dir_url(__FILE__));
define('BOOKGPT_PLUGIN_BASENAME', plugin_basename(__FILE__));

/**
 * The code that runs during plugin activation.
 */
function activate_bookgpt() {
    require_once BOOKGPT_PLUGIN_DIR . 'includes/class-bookgpt-activator.php';
    BookGPT_Activator::activate();
}

/**
 * The code that runs during plugin deactivation.
 */
function deactivate_bookgpt() {
    require_once BOOKGPT_PLUGIN_DIR . 'includes/class-bookgpt-deactivator.php';
    BookGPT_Deactivator::deactivate();
}

register_activation_hook(__FILE__, 'activate_bookgpt');
register_deactivation_hook(__FILE__, 'deactivate_bookgpt');

/**
 * The core plugin class that is used to define internationalization,
 * admin-specific hooks, and public-facing site hooks.
 */
require_once BOOKGPT_PLUGIN_DIR . 'includes/class-bookgpt-loader.php';
require_once BOOKGPT_PLUGIN_DIR . 'includes/class-bookgpt-api.php';
require_once BOOKGPT_PLUGIN_DIR . 'includes/class-bookgpt-analytics.php';
require_once BOOKGPT_PLUGIN_DIR . 'admin/class-bookgpt-admin.php';
require_once BOOKGPT_PLUGIN_DIR . 'public/class-bookgpt-public.php';

/**
 * Begins execution of the plugin.
 */
function run_bookgpt() {
    $plugin = new BookGPT_Loader();
    $plugin->run();
}

/**
 * Add custom links to plugin page
 */
function bookgpt_plugin_action_links($links) {
    $settings_link = '<a href="admin.php?page=bookgpt-settings">' . __('Settings', 'bookgpt-wp') . '</a>';
    array_unshift($links, $settings_link);
    
    return $links;
}
add_filter('plugin_action_links_' . BOOKGPT_PLUGIN_BASENAME, 'bookgpt_plugin_action_links');

/**
 * Add a webhook endpoint for tracking API usage
 */
function bookgpt_api_usage_webhook() {
    register_rest_route('bookgpt/v1', '/usage', array(
        'methods' => 'POST',
        'callback' => 'bookgpt_process_api_usage_webhook',
        'permission_callback' => '__return_true'
    ));
}
add_action('rest_api_init', 'bookgpt_api_usage_webhook');

/**
 * Process API usage webhook data
 */
function bookgpt_process_api_usage_webhook($request) {
    $data = $request->get_json_params();
    
    // Verify webhook signature if provided
    $options = get_option('bookgpt_options');
    $webhook_secret = isset($options['webhook_secret']) ? $options['webhook_secret'] : '';
    
    if (!empty($webhook_secret)) {
        $signature = $request->get_header('X-BookGPT-Signature');
        if (empty($signature)) {
            return new WP_Error('invalid_signature', 'Missing webhook signature', array('status' => 403));
        }
        
        $payload = $request->get_body();
        $expected_signature = hash_hmac('sha256', $payload, $webhook_secret);
        
        if (!hash_equals($expected_signature, $signature)) {
            return new WP_Error('invalid_signature', 'Invalid webhook signature', array('status' => 403));
        }
    }
    
    // Process usage data
    $api = new BookGPT_API();
    $result = $api->process_usage_webhook($data);
    
    if ($result === false) {
        return new WP_Error('invalid_data', 'Invalid webhook data', array('status' => 400));
    }
    
    return array('success' => true);
}

/**
 * Create database tables on plugin activation
 */
function bookgpt_create_db_tables() {
    global $wpdb;
    $charset_collate = $wpdb->get_charset_collate();
    
    // Table for tracking chat interactions
    $table_name = $wpdb->prefix . 'bookgpt_interactions';
    $sql = "CREATE TABLE $table_name (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        session_id varchar(50) NOT NULL,
        user_id bigint(20) NULL,
        user_message text NOT NULL,
        bot_response text NOT NULL,
        books_recommended text NULL,
        ip_address varchar(45) NULL,
        page_url varchar(255) NULL,
        timestamp datetime NOT NULL,
        PRIMARY KEY  (id),
        KEY session_id (session_id),
        KEY user_id (user_id),
        KEY timestamp (timestamp)
    ) $charset_collate;";
    
    // Table for tracking conversions (book clicks)
    $table_name = $wpdb->prefix . 'bookgpt_conversions';
    $sql .= "CREATE TABLE $table_name (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        session_id varchar(50) NOT NULL,
        user_id bigint(20) NULL,
        book_title varchar(255) NOT NULL,
        book_author varchar(255) NULL,
        amazon_link text NOT NULL,
        timestamp datetime NOT NULL,
        converted tinyint(1) DEFAULT 0,
        revenue decimal(10,2) DEFAULT 0,
        PRIMARY KEY  (id),
        KEY session_id (session_id),
        KEY user_id (user_id),
        KEY timestamp (timestamp)
    ) $charset_collate;";
    
    // Table for tracking API usage
    $table_name = $wpdb->prefix . 'bookgpt_api_usage';
    $sql .= "CREATE TABLE $table_name (
        id bigint(20) NOT NULL AUTO_INCREMENT,
        api_type varchar(50) NOT NULL,
        tokens_used int(11) NOT NULL DEFAULT 0,
        cost decimal(10,5) NOT NULL DEFAULT 0,
        timestamp datetime NOT NULL,
        PRIMARY KEY  (id),
        KEY api_type (api_type),
        KEY timestamp (timestamp)
    ) $charset_collate;";
    
    require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
    dbDelta($sql);
}
register_activation_hook(__FILE__, 'bookgpt_create_db_tables');

/**
 * Add missing hooks and actions
 */
add_action('init', 'bookgpt_register_shortcodes');
add_action('wp_enqueue_scripts', 'bookgpt_enqueue_public_scripts');
add_action('admin_enqueue_scripts', 'bookgpt_enqueue_admin_scripts');
add_action('admin_menu', 'bookgpt_add_admin_menu');
add_action('admin_init', 'bookgpt_register_settings');

// Initialize the plugin
run_bookgpt();
