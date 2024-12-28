function sw --description 'AWS profile switcher'
    argparse h/help -- $argv 2>/dev/null
    or begin
        __sw_print_usage
        return 1
    end

    if set -q _flag_help
        __sw_print_usage
        return 0
    end

    if test (count $argv) -eq 0
        __sw_show_picker_and_switch
    else
        __sw_switch_profile $argv[1]
    end
end

function __sw_print_usage
    echo "Usage: sw [profile]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo
    echo "Examples:"
    echo "  sw           # Interactive profile picker"
    echo "  sw prod      # Switch directly to 'prod' profile"
end

function __sw_show_picker_and_switch
    set -l current_profile $AWS_PROFILE
    set -l current_region $AWS_REGION

    if set -l profile (aws configure list-profiles | sort | fzf \
        --reverse \
        --header "Current: $current_profile ($current_region)" \
        --prompt="Select AWS Profile > " \
        --preview 'aws configure get region --profile {}; echo; aws configure list --profile {}')
        __sw_switch_profile $profile
    else
        echo "No profile selected"
        return 1
    end
end

function __sw_switch_profile
    set -l profile $argv[1]
    set -l profiles (aws configure list-profiles)

    if not contains "$profile" $profiles
        echo "Error: Profile '$profile' does not exist."
        echo "Available profiles: "(string join ', ' $profiles)
        return 1
    end

    if test "$profile" = "$AWS_PROFILE"
        echo "Already using profile $profile"
        return 0
    end

    # Store old values for rollback
    set -l old_profile $AWS_PROFILE
    set -l old_region $AWS_REGION

    set -gx AWS_PROFILE $profile

    if not aws sso login 2>/dev/null
        echo "SSO login failed. Rolling back to previous profile."
        set -gx AWS_PROFILE $old_profile
        set -gx AWS_REGION $old_region
        return 1
    end

    if set -l new_region (aws configure get region 2>/dev/null)
        set -gx AWS_REGION $new_region
        set -gx AWS_DEFAULT_REGION $new_region
        echo "✓ Switched to $AWS_PROFILE in region $AWS_REGION"
    else
        echo "Warning: Could not get region for profile $profile"
        echo "✓ Switched to $AWS_PROFILE (region unchanged)"
    end

    if not aws sts get-caller-identity >/dev/null 2>&1
        echo "Warning: Could not verify AWS credentials"
    end

    return 0
end
