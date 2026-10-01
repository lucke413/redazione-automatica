<?php
/**
 * Plugin Name: Editorial Bridge
 * Description: Metadati SEO e riepilogo redazione per il nuovo progetto. Gratuito, senza servizi esterni.
 * Version: 1.0
 */
if (!defined('ABSPATH')) exit;
add_action('rest_api_init', function () {
    register_rest_route('editorial/v1', '/status', [
        'methods'=>'GET', 'permission_callback'=>function(){return current_user_can('edit_posts');},
        'callback'=>function(){return ['version'=>'1.0'];}
    ]);
    register_rest_field('post', 'editorial_seo', [
        'get_callback'=>function($post){ return get_post_meta($post['id'], '_editorial_seo', true) ?: (object)[]; },
        'update_callback'=>function($value, $post){
            if (!current_user_can('edit_post', $post->ID)) return new WP_Error('forbidden','Permesso negato',['status'=>403]);
            if (!is_array($value)) return new WP_Error('invalid','Oggetto richiesto',['status'=>400]);
            $clean=[];
            foreach (['seo_title','seo_description','focus_keyphrase'] as $k) $clean[$k]=sanitize_text_field($value[$k] ?? '');
            update_post_meta($post->ID, '_editorial_seo', $clean);
            return true;
        },
        'schema'=>['type'=>'object','context'=>['view','edit'],'properties'=>[
            'seo_title'=>['type'=>'string'],'seo_description'=>['type'=>'string'],'focus_keyphrase'=>['type'=>'string']
        ]]
    ]);
});
// Non duplicare meta di plugin SEO già presenti; integrare il loro mapping prima di attivarli.
function editorial_has_seo_plugin(){return defined('WPSEO_VERSION') || defined('RANK_MATH_VERSION') || defined('AIOSEO_VERSION');}
add_filter('pre_get_document_title', function($title){
    if (is_singular('post') && !editorial_has_seo_plugin()) {
        $seo=get_post_meta(get_queried_object_id(),'_editorial_seo',true);
        if (!empty($seo['seo_title'])) return $seo['seo_title'];
    }
    return $title;
});
add_action('wp_head', function(){
    if (!is_singular('post') || editorial_has_seo_plugin()) return;
    $id=get_queried_object_id();$seo=get_post_meta($id,'_editorial_seo',true);
    if (!empty($seo['seo_description'])) echo '<meta name="description" content="'.esc_attr($seo['seo_description']).'">'."\n";
    $title=$seo['seo_title'] ?? get_the_title($id);
    echo '<meta property="og:title" content="'.esc_attr($title).'">'."\n";
    echo '<meta property="og:description" content="'.esc_attr($seo['seo_description'] ?? '').'">'."\n";
    echo '<meta property="og:url" content="'.esc_url(get_permalink($id)).'">'."\n";
    echo '<meta property="og:type" content="article">'."\n";
    $image=get_the_post_thumbnail_url($id,'full');
    if ($image) echo '<meta property="og:image" content="'.esc_url($image).'">'."\n";
    $schema=['@context'=>'https://schema.org','@type'=>'Article','headline'=>get_the_title($id),'datePublished'=>get_the_date(DATE_W3C,$id),'dateModified'=>get_the_modified_date(DATE_W3C,$id),'mainEntityOfPage'=>get_permalink($id),'publisher'=>['@type'=>'Organization','name'=>get_bloginfo('name')]];
    if ($image) $schema['image']=[$image];
    echo '<script type="application/ld+json">'.wp_json_encode($schema,JSON_HEX_TAG|JSON_HEX_AMP|JSON_HEX_APOS|JSON_HEX_QUOT).'</script>';
}, 5);
add_action('admin_menu',function(){
    add_menu_page('Redazione','Redazione','edit_posts','editorial-dashboard',function(){
        if (!current_user_can('edit_posts')) return;
        echo '<div class="wrap"><h1>Redazione</h1><p>Obiettivo: 20 articoli al giorno. I contenuti da verificare restano in bozza. Facebook è manuale.</p>';
        foreach (['draft'=>'Da revisionare','future'=>'Programmati','publish'=>'Pubblicati'] as $status=>$label) {
            echo '<h2>'.esc_html($label).'</h2><ul>';
            $posts=get_posts(['post_type'=>'post','post_status'=>$status,'numberposts'=>20]);
            foreach ($posts as $p) echo '<li><a href="'.esc_url(get_edit_post_link($p->ID)).'">'.esc_html($p->post_title).'</a> — '.esc_html($p->post_date).'</li>';
            echo '</ul>';
        }
        echo '<p>Traffico e ricavi: usare i pannelli AlterVista e AdSense. Apprendimento automatico non ancora attivo.</p></div>';
    },'dashicons-media-document');
});
