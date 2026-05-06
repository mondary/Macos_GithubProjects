#!/bin/bash

# Script de mise à jour du hub de projets
# Usage: ./update-hub.sh

BASE_DIR="/Users/clm/Documents/GitHub"
OUTPUT="$BASE_DIR/hub_projects.json"

echo "Scanning projects..."

# Fonction pour extraire la première ligne de description du README
get_description() {
    local readme="$1"
    if [[ -f "$readme" ]]; then
        grep -v "^#" "$readme" | grep -v "^$" | grep -v "^\`\`\`" | head -1 | sed 's/"/\\"/g' | cut -c1-200
    fi
}

# Fonction pour trouver une image
find_image() {
    local dir="$1"
    local img=$(find "$dir" -maxdepth 3 \( -name "*.png" -o -name "*.jpg" -o -name "*.gif" \) \
        ! -path "*/node_modules/*" ! -path "*/.git/*" ! -name "Icon*" ! -name "icon_*" \
        2>/dev/null | head -1)
    if [[ -n "$img" ]]; then
        echo "${img#$BASE_DIR/}"
    fi
}

# Fonction pour détecter les tags depuis le contenu du projet
detect_tags() {
    local dir="$1"
    local tags=""

    [[ -f "$dir/package.json" ]] && tags="Node.js"
    [[ -f "$dir/Cargo.toml" ]] && tags="${tags:+$tags,}Rust"
    [[ -f "$dir/go.mod" ]] && tags="${tags:+$tags,}Go"
    [[ -f "$dir/requirements.txt" ]] && tags="${tags:+$tags,}Python"
    [[ -f "$dir/Gemfile" ]] && tags="${tags:+$tags,}Ruby"
    [[ -f "$dir/composer.json" ]] && tags="${tags:+$tags,}PHP"
    [[ -f "$dir/manifest.json" ]] && tags="${tags:+$tags,}Chrome"

    # Swift
    if ls "$dir"/*.xcodeproj 1>/dev/null 2>&1 || [[ -f "$dir/Package.swift" ]]; then
        tags="${tags:+$tags,}Swift"
    fi

    # WordPress
    if [[ -f "$dir/style.css" && -f "$dir/functions.php" ]]; then
        tags="${tags:+$tags,}WordPress"
    fi

    # Bash scripts
    if ls "$dir"/*.sh 1>/dev/null 2>&1; then
        tags="${tags:+$tags,}Bash"
    fi

    echo "$tags"
}

# Fonction pour obtenir l'icône selon la catégorie/nom
get_icon() {
    local name="$1"
    local cat="$2"

    case "$name" in
        *dict*|*Dict*) echo "📖" ;;
        *transcript*|*Transcript*|*dictation*) echo "🎙️" ;;
        *mail*|*Mail*|*gmail*|*Gmail*) echo "📧" ;;
        *note*|*Note*) echo "📝" ;;
        *menu*|*Menu*) echo "📺" ;;
        *cuisto*|*recipe*) echo "👨‍🍳" ;;
        *crypto*|*btc*) echo "₿" ;;
        *rubik*) echo "🧊" ;;
        *steam*|*game*|*Game*) echo "🎮" ;;
        *cv*|*CV*|*portfolio*) echo "📄" ;;
        *theme*|*style*|*Stylus*) echo "🎨" ;;
        *translate*|*Translate*) echo "🌍" ;;
        *linkedin*|*LinkedIn*) echo "💼" ;;
        *git*|*Git*) echo "🚀" ;;
        *terminal*|*Terminal*|*cli*|*CLI*) echo "💻" ;;
        *api*|*API*|*server*|*Server*) echo "🔌" ;;
        *agent*|*gpt*|*GPT*|*ia*|*IA*) echo "🤖" ;;
        *wallpaper*|*Wallpaper*) echo "🖼️" ;;
        *cleanup*|*Cleanup*|*archive*) echo "🧹" ;;
        *clipboard*) echo "📋" ;;
        *permission*) echo "🔐" ;;
        *highlight*) echo "🌟" ;;
        *sticky*) echo "📌" ;;
        *rss*) echo "📰" ;;
        *tab*|*Tab*) echo "🪟" ;;
        *wp*|*WP*|*wordpress*) echo "⚙️" ;;
        *)
            case "$cat" in
                apps) echo "🍎" ;;
                extensions) echo "🧩" ;;
                web) echo "🌐" ;;
                server) echo "🖥️" ;;
                *) echo "📁" ;;
            esac
            ;;
    esac
}

# Démarre le JSON
echo "[" > "$OUTPUT"
first=true

# Catégories à scanner
FOLDERS="APPS EXTENSIONS WEB SERVER"

for folder in $FOLDERS; do
    case "$folder" in
        APPS) category="apps" ;;
        EXTENSIONS) category="extensions" ;;
        WEB) category="web" ;;
        SERVER) category="server" ;;
    esac

    dir="$BASE_DIR/$folder"

    [[ ! -d "$dir" ]] && continue

    for project in "$dir"/*/; do
        [[ ! -d "$project" ]] && continue

        name=$(basename "$project")

        # Skip hidden folders and special folders
        [[ "$name" == .* ]] && continue
        [[ "$name" == "A TRIER" ]] && continue
        [[ "$name" == "node_modules" ]] && continue

        # Cherche le README
        readme=""
        for r in "$project/README.md" "$project/readme.md" "$project/README.txt"; do
            [[ -f "$r" ]] && readme="$r" && break
        done

        description=$(get_description "$readme")
        [[ -z "$description" ]] && description="Projet $name"

        image=$(find_image "$project")
        tags=$(detect_tags "$project")
        icon=$(get_icon "$name" "$category")

        # Nettoie le titre
        title=$(echo "$name" | sed 's/^Macos_//;s/^Chrome_//;s/^Web_//;s/^VS_//;s/^WP_//;s/_/ /g')

        # Ajoute la virgule si pas le premier
        [[ "$first" != true ]] && echo "," >> "$OUTPUT"
        first=false

        # Formatte les tags en JSON
        if [[ -n "$tags" ]]; then
            tags_json=$(echo "$tags" | sed 's/,/","/g;s/^/"/;s/$/"/')
        else
            tags_json=""
        fi

        # Écrit l'objet JSON
        if [[ -n "$image" ]]; then
            image_json="\"$image\""
        else
            image_json="null"
        fi

        cat >> "$OUTPUT" << EOF
  {
    "title": "$title",
    "description": "$description",
    "category": "$category",
    "tags": [$tags_json],
    "icon": "$icon",
    "image": $image_json,
    "folder": "$name"
  }
EOF
    done
done

echo "" >> "$OUTPUT"
echo "]" >> "$OUTPUT"

# Compte les projets
total=$(grep -c '"title"' "$OUTPUT")
echo "Done! $total projects found."
echo "Output: $OUTPUT"
