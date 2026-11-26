<?php

declare(strict_types=1);

/** Read-only: verify the two public files used when native XSLT is absent. */
function verifyFlarumXsltAssets(string $root): array
{
    if (!is_file($root.'/vendor/flarum/core/src/Formatter/XsltPolyfill.php')) {
        return ['required' => false]; // Older Core versions do not emit this loader.
    }
    $source = $root.'/vendor/flarum/core/js/dist/xslt-polyfill/';
    $public = $root.'/public/assets/xslt-polyfill/';
    $verified = [];
    foreach (['xslt-polyfill.min.js', 'dist/xslt-wasm.js'] as $relative) {
        foreach ([$source.$relative, $public.$relative] as $path) {
            if (!is_readable($path) || !is_file($path) || filesize($path) === 0) {
                throw new RuntimeException('Missing or empty XSLT asset: '.$relative);
            }
        }
        $hash = hash_file('sha256', $source.$relative);
        if (!hash_equals($hash, hash_file('sha256', $public.$relative))) {
            throw new RuntimeException('Published XSLT asset differs from installed Core: '.$relative);
        }
        $verified[$relative] = $hash;
    }
    return ['required' => true, 'verified' => $verified];
}

if (realpath($_SERVER['SCRIPT_FILENAME'] ?? '') === __FILE__) {
    $root = $argv[1] ?? '';
    $allowed = getenv('TECHFLOW_ALLOWED_FLARUM_ROOT') ?: '/srv/techflow-flarum-staging/app';
    if (PHP_SAPI !== 'cli' || !$root || $root === '/' || realpath($root) === false || realpath($root) !== realpath($allowed)) {
        fwrite(STDERR, "Unexpected Flarum application path\n");
        exit(2);
    }
    try {
        fwrite(STDOUT, json_encode(verifyFlarumXsltAssets($root), JSON_UNESCAPED_SLASHES)."\n");
    } catch (Throwable $error) {
        fwrite(STDERR, $error->getMessage()."\n");
        exit(1);
    }
}
